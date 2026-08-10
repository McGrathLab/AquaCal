# Phase 21: New-Feature Documentation & Dataset Refresh - Pattern Map

**Mapped:** 2026-08-10
**Files analyzed:** 13 (3 new, 10 modified)
**Analogs found:** 11 / 13 (2 have no true analog and must be built from RESEARCH/CONTEXT alone)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `docs/guide/benchmarking.md` | config/docs page | request-response (reference doc) | `docs/guide/configuration.md` | exact (same doc family, same job: field-by-field reference table) |
| `docs/tutorials/<cli-tutorial>.md` | tutorial/docs page | batch (walkthrough narrating a CLI run) | `docs/guide/cli.md` (structure) + `docs/tutorials/index.md`/notebook 01 (narrative/tutorial framing) | role-match (no existing `.md` tutorial; `cli.md` is reference not walkthrough) |
| `scripts/<frame-extractor>.py` | utility/script (batch file I/O) | batch, file-I/O | `experiments/e2_real_rig.py` (script shape) + `src/aquacal/io/video.py`/`images.py` (the reused surface) | role-match (no `scripts/` precedent exists at all; nearest runnable-script precedent is `experiments/`) |
| `src/aquacal/datasets/data/manifest.json` | config (data file) | CRUD (record update) | itself (edit in place) | exact |
| `docs/guide/configuration.md` (~97/109, ~244-245) | docs page | request-response | itself (edit in place) | exact |
| `docs/guide/refractive_geometry.md` (~117) | docs page | request-response | itself (edit in place) | exact |
| `docs/tutorials/index.md` + nav | docs index/nav | request-response | itself (edit in place); `docs/index.md` toctree for nav syntax | exact |
| `docs/tutorials/01_full_pipeline.ipynb` | tutorial notebook | batch (interactive walkthrough) | itself (edit in place); `docs/tutorials/02_synthetic_validation.ipynb` for sibling structure | exact |
| `docs/tutorials/02_synthetic_validation.ipynb` | tutorial notebook | batch | itself (edit in place); notebook 01 for sibling structure | exact |
| `pyproject.toml` / `requirements.txt` | config | CRUD (dependency pin) | itself (edit in place) | exact |
| `.pre-commit-config.yaml` | config | CRUD | itself (edit in place) | exact |
| `experiments/results/` (5 files removed) | data artifacts | file-I/O (deletion) | n/a — deletion, no analog needed | n/a |
| `.planning/REQUIREMENTS.md` | docs/planning | request-response | itself (edit in place) | exact |

## Pattern Assignments

### `docs/guide/benchmarking.md` (new guide page)

**Analog:** `docs/guide/configuration.md` (316 lines) — same doc family (`docs/guide/`), same
job (document a machine-produced artifact field-by-field with type/default/meaning tables), same
admonition and cross-reference conventions. `docs/guide/optimizer.md` is a secondary analog for
math-block and mermaid-diagram conventions if benchmarking.md needs to show formulas (unlikely,
but the trace-column "cost/step-norm/optimality" explanation may want one).

**Opening pattern** (`docs/guide/configuration.md:1-11`):
```markdown
# Configuration Reference

AquaCal calibration runs are driven entirely by a YAML configuration file. All distances are
in meters. Run `aquacal init --intrinsic-dir ... --extrinsic-dir ...` to generate a starting
config scanned from your video directories, then edit it by hand for your rig.

This page documents every top-level YAML section in the order they appear in
`example_config.yaml`, plus several always-on v1.7/v1.8 behaviors that have no config key of
their own. For the exhaustive dataclass field list (including types and validation), see
{class}`aquacal.config.schema.CalibrationConfig` in the [API reference](../api/config.rst).
```
Use the same opening shape for benchmarking.md: one-paragraph purpose statement, then a
paragraph naming what this page documents (benchmark.json fields, trace CSV columns,
conditioning `.npz` contents) and pointing to the writer module for exhaustive detail
(`experiments/_io.py`'s `assemble_benchmark_record`/`write_benchmark_json`, imported from
`aquacal.io`, is the "always up to date" fallback the way `CalibrationConfig` is here).

**Section header + table pattern** (`docs/guide/configuration.md:87-98`):
```markdown
## interface

Refractive interface (air-water boundary) parameters.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `n_air` | float | `1.0` | Refractive index of air |
| `n_water` | float | `1.333` | Refractive index of water (fresh water at 20C) |
...

```yaml
interface:
  n_air: 1.0
  n_water: 1.333
  ...
```
```
For benchmark.json (JSON, not YAML), swap the trailing fenced block's language tag to `json`
and use a real trimmed excerpt from `experiments/results/benchmark.json` (D-02's cited live
schema instance) instead of a hand-written example — this keeps the page grounded the way
configuration.md's YAML snippets are grounded in `example_config.yaml`.

**Admonition pattern for "gotcha"/"ablation option" style boxes** (two variants seen):
```markdown
:::{admonition} shared_interface is an ablation option, not a recommended setting
:class: warning

`shared_interface` defaults to `true`: ...
:::
```
and (`docs/guide/refractive_geometry.md:105-115`):
```markdown
:::{admonition} Gotcha: water_z is a Z-coordinate, not a distance
:class: warning
...
:::
```
D-03's camera-height/interface-distance correlation-block discussion (tied to MF-12) reads
naturally as a `:class: note` or `:class: tip` admonition following this same pattern, cross-
referencing `docs/guide/optimizer.md`'s "Sparse Jacobian Strategy" section (parameter ordering)
since the conditioning `.npz`'s correlation matrix is indexed by the same parameter vector
documented there (`docs/guide/optimizer.md:83-100`).

**Cross-reference / "See Also" footer pattern** (`docs/guide/configuration.md:311-316`):
```markdown
## See Also

- [CLI Reference](cli.md) — Command-line usage and options
- [Optimizer Pipeline](optimizer.md) — Understanding the calibration stages
- [Troubleshooting](troubleshooting.md) — Diagnosing and fixing common calibration issues
- [Glossary](glossary.md) — Definitions of key terms
```
Reuse verbatim shape; benchmarking.md should link back to `configuration.md#internals` (the
`save_optimization_trace`/`save_conditioning` flags that produce what this page documents) and
to `optimizer.md` (parameter vector layout, needed to read the conditioning correlation matrix).

**Existing content this page supersedes/expands** — `docs/guide/configuration.md:235-252`
(the `internals` section, two one-line rows for `save_optimization_trace` / `save_conditioning`)
stays as the config-flag reference; benchmarking.md is the new output-schema deep dive it links
to (per D-03, do not delete the existing rows, add a forward link from them).

**Data source for content** (not a doc analog, but the concrete inputs the page must describe):
`experiments/results/benchmark.json` (the live schema instance named in CONTEXT.md), and
`experiments/_io.py`'s `assemble_benchmark_record`/`capture_environment`/`write_benchmark_json`
imports (from `aquacal.io`) are the producing functions — read those signatures/docstrings when
drafting the field table rather than reverse-engineering purely from the JSON.

---

### `docs/tutorials/<cli-tutorial>.md` (new tutorial page)

**Two analogs, different jobs:**

1. **Structural/reference analog:** `docs/guide/cli.md` (197 lines) — already documents
   `aquacal calibrate`, `aquacal init`, `aquacal compare` with syntax blocks, argument tables,
   and numbered example blocks. The new tutorial's individual command invocations should match
   this page's fenced-bash conventions exactly:
   ```markdown
   **Syntax:**
   ```bash
   aquacal calibrate <config_path> [options]
   ```
   ```
   and its **Examples** numbered-comment style:
   ```markdown
   **Examples:**

   ```bash
   # Run calibration with default settings
   aquacal calibrate config.yaml

   # Run with verbose output to see optimizer progress
   aquacal calibrate config.yaml -v
   ```
   ```

2. **Narrative/tutorial-framing analog:** `docs/tutorials/01_full_pipeline.ipynb`'s markdown
   cells (cell 0 title+prereqs, cell 2 "Data Source Selection" options list, cell 22's
   Markdown troubleshooting table) — these establish the tutorials' voice: short intro
   paragraph, bulleted option list with bold lead terms, a `| Symptom | Likely Cause | Fix |`
   table for troubleshooting. Since D-05 places the real-dataset walkthrough here (the zenodo
   branch is being deleted from the notebook), lift this narrative framing rather than the
   `cli.md` reference framing for the prose sections; use `cli.md`'s framing only for the
   individual command blocks.

**Nav entry precedent** — see the nbsphinx/toctree section below; the tutorial gets a bullet
in `docs/tutorials/index.md` matching the two existing entries' shape (`## Tutorial NN: Title`
+ one paragraph + "**Start here** if ...", see below) and a bare filename-stem line in the
hidden toctree.

**D-06's "quote numbers from the archive's reference outputs" requirement** — the concrete
precedent for "a source file named inline so a reader can diff against it" is
`docs/guide/optimizer.md`'s numbered-parameter-count callouts, e.g. (`optimizer.md:190-195`):
```markdown
For a 13-camera, 100-frame rig, the parameter count depends on which options
are enabled:
- **673** parameters with the interface normal fixed (the default)
```
and the test-backed claim at the bottom of that section:
```markdown
These numbers are asserted live against the shipped code in
`tests/unit/test_optim_common.py::TestDocumentedGroupingNumbers`.
```
For the CLI tutorial, the equivalent phrasing is "these numbers are read from
`<archive-path>/reference_outputs/calibration.json`" (or whatever DATA-01b names the shipped
reference file) named inline next to every quoted number, per D-06.

---

### `scripts/<frame-extractor>.py` (new, creates `scripts/`)

**No true analog exists** — `scripts/` does not exist yet, and there is no committed,
non-package, runnable extraction script anywhere in the repo. The closest precedents are
split across two places:

1. **Script/CLI shape (argparse, `main()`, logging):** `experiments/e2_real_rig.py`
   (`experiments/e2_real_rig.py:834-987`). Its five-flag shared contract
   (`experiments/_io.py:43-87`, `build_experiment_arg_parser`) is experiment-suite-specific
   machinery (`--smoke`/`--check`/`--force` resumability, baseline-comparison) that the
   extractor script should **not** import wholesale — D-11 explicitly keeps this out of
   `experiments/` and out of public API, so it owes no `--check`/`--smoke` contract. Copy only
   the shape:
   ```python
   def build_arg_parser() -> argparse.ArgumentParser:
       parser = argparse.ArgumentParser(description=__doc__)
       parser.add_argument(...)
       return parser

   def main(argv: list[str] | None = None) -> int:
       parser = build_arg_parser()
       args = parser.parse_args(argv)
       logging.basicConfig(level=logging.INFO, format="%(message)s")
       ...
       return 0

   if __name__ == "__main__":
       sys.exit(main())
   ```
   (`experiments/e2_real_rig.py:961-987`, trimmed to remove the smoke/check/band-config
   branches that don't apply here).

2. **The I/O surface to call, not reimplement** (D-11's explicit instruction) —
   `src/aquacal/io/video.py`'s `VideoSet`:
   ```python
   class VideoSet:
       def __init__(self, video_paths: dict[str, str]) -> None: ...

       def iterate_frames(
           self, start: int = 0, stop: int | None = None, step: int = 1,
       ) -> Iterator[tuple[int, dict[str, NDArray[np.uint8] | None]]]:
           ...
   ```
   (`src/aquacal/io/video.py:35-49`, `186-217`). The extractor should open a `VideoSet` with a
   single-camera `{camera_name: avi_path}` dict per call (or extend it to loop all 13 cameras
   with one `VideoSet` covering all paths at once — `VideoSet` is inherently multi-camera and
   `step=30` is honored directly by `iterate_frames(step=frame_step)`), then write each
   returned frame with `cv2.imwrite` as **lossless PNG** (D-07/D-08: `cv2.imwrite(path, frame)`
   with a `.png` suffix is lossless by default — no extra flags needed, unlike JPEG's
   `IMWRITE_JPEG_QUALITY`).

   The **read-back contract** the extractor's output must satisfy is `ImageSet`
   (`src/aquacal/io/images.py:76-122`): it natsorts files by name within each camera directory
   and requires the same count in every directory. `ImageSet`'s extensions set already includes
   `.png` (`src/aquacal/io/images.py:86`: `{".jpg", ".jpeg", ".png"}`), so no `ImageSet` change
   is needed — only matching the naming convention.

   **Current staged-archive filename convention to match** (confirmed on disk at
   `docs/tutorials/aquacal_data/real-rig/real-rig/extrinsic/<camera>/`):
   ```
   frame0000.jpg
   frame0001.jpg
   ...
   ```
   i.e. `frame{idx:04d}.<ext>`, zero-padded to 4 digits, one subdirectory per camera named by
   camera id (e.g. `e3v8250`). `natsorted` handles any consistent zero-padding, but 4-digit
   padding is what's already shipped and is safe up to 9999 frames (262 usable extrinsic frames
   and far fewer intrinsic frames both fit comfortably). The extractor should preserve this
   `frame{idx:04d}.png` naming (only the extension changes, jpg -> png, per D-07/D-08), and the
   same `<extrinsic|intrinsic>/<camera_name>/` two-level directory layout.

**Package-boundary note:** because `scripts/` is not inside `src/aquacal/`, it is exempt from
`.claude/rules/source-code.md`'s `__init__.py`/`__all__` requirements (those apply to package
code only) — no `scripts/__init__.py` is required, though a module docstring at the top of the
extractor script is still required project-wide (per CLAUDE.md code-style rules).

---

### `src/aquacal/datasets/data/manifest.json` (modified in place)

**Analog:** itself — this is a direct field edit, not a pattern-copy. Current full content:
```json
{
  "version": "1.0",
  "datasets": {
    "real-rig": {
      "type": "real",
      "included": false,
      "zenodo_record_id": 18645385,
      "zenodo_filename": "real-rig-calib.zip",
      "checksum": "md5:c66380aaa8cbca6bc04a3157baacbee8",
      "size_bytes": 164023590,
      "description": "9+ camera production rig — download from Zenodo"
    }
  }
}
```
(`src/aquacal/datasets/data/manifest.json:1-14`). DATA-02 changes exactly three fields:
`zenodo_record_id`, `checksum`, `size_bytes` (per CONTEXT.md's explicit scope) — `description`
and `zenodo_filename` are not listed as changing, but D-14's gate 2 also validates the
extraction path (`loader.py:60`'s nested-layout check), so if the new zip's internal top-level
folder name differs, `zenodo_filename` would need updating too; verify against the actual
staged zip name before finalizing.

**Consumers to keep in sync (read-only reference, not files this phase edits):**
`src/aquacal/datasets/_manifest.py` (`get_dataset_info`) and
`src/aquacal/datasets/download.py:151-171` (`download_and_extract`, reading
`zenodo_record_id`/`zenodo_filename`/`checksum` verbatim) — both already generic; no code
change needed, confirmed by CONTEXT.md's "Reusable assets" note.

---

### `docs/guide/configuration.md` (verify-only edit, D-04)

**Existing `shared_interface` documentation to verify, not rewrite** (`configuration.md:97`,
`configuration.md:109-118`):
```markdown
| `shared_interface` | bool | `true` | Analysis/ablation option — see below |
...
:::{admonition} shared_interface is an ablation option, not a recommended setting
:class: warning

`shared_interface` defaults to `true`: all cameras share a single global `water_z`, which is
the shared-interface assumption underlying AquaCal's central modeling claim. Setting it to
`false` gives each camera its own independently-optimized `water_z`, which exists only for
degeneracy/ablation analysis (e.g. quantifying how tightly the shared value is actually
constrained by the data). Do not use per-camera mode for production calibration — it is not a
co-equal alternative to the shared model.
:::
```
D-03's expanded `internals` rows (`configuration.md:241-245`) live in the same file just above
`## seed`:
```markdown
| `save_optimization_trace` | bool | `false` | Per-iteration CSV trace (cost, step norm, optimality) for each bundle-adjustment stage |
| `save_conditioning` | bool | `false` | Jacobian singular-value spectrum and full parameter correlation matrix at the solution. Expensive — off by default. |
```
These two rows should each gain a forward link to the new `benchmarking.md` page (e.g.
"— see [Benchmarking & Diagnostics](benchmarking.md) for the CSV/`.npz` schema").

---

### `docs/guide/refractive_geometry.md` (verify-only edit, D-04)

**Existing admonition to verify** (`refractive_geometry.md:117-127`):
```markdown
:::{admonition} Ablation option: per-camera water_z (`shared_interface: false`)
:class: note

By default all cameras share a single global `water_z`. An opt-in config flag,
`interface.shared_interface: false`, instead gives each optimized camera its own
`water_z` parameter. This exists **only for degeneracy/ablation analysis** (e.g.
the WP6 experiment that measures the per-camera `water_z` spread) and is **not a
recommended production setting** — the shared-interface assumption underlies the
library's core accuracy claim. A full worked example is deferred to a later
documentation pass.
:::
```
D-04 says wording verification only — no content pattern needed beyond confirming this still
matches current behavior/terminology.

---

### `docs/tutorials/index.md` and nav/toctree (nbsphinx question 2)

**Current full file** (`docs/tutorials/index.md:1-26`):
```markdown
# Tutorials

Interactive Jupyter notebook tutorials demonstrating AquaCal's calibration pipeline with real and synthetic data.

Each tutorial is self-contained and can be run locally or on Google Colab.

## Tutorial 01: Calibrate Your Rig

End-to-end calibration from data loading to validated 3D results. Covers ChArUco detection, intrinsic/extrinsic initialization, joint refractive bundle adjustment, and a built-in diagnostics section for interpreting reprojection errors, checking interface distance recovery, and troubleshooting common issues.

**Start here** if you want to calibrate a real or synthetic underwater multi-camera rig.

## Tutorial 02: Why Refractive Calibration Matters

Controlled synthetic experiments that quantify what you gain from modeling Snell's law refraction. Compares refractive vs non-refractive calibration on the same data — showing how non-refractive models introduce systematic bias in focal length and camera position even when reprojection error looks acceptable.

**Start here** if you want to understand when the refractive model is essential and how to validate parameter recovery accuracy.

:::{toctree}
:maxdepth: 1
:hidden:

01_full_pipeline
02_synthetic_validation
:::
```

**Confirmed: a `.md` page CAN sit in the same toctree as `.ipynb` files.** MyST-parser's
`{toctree}` directive resolves entries by document stem regardless of source suffix (`.md` vs
`.ipynb`), exactly like the root `docs/index.md` toctree already mixes `.md` pages
(`overview`, `guide/index`) with directory indices — there is no nbsphinx-specific restriction
here; nbsphinx only changes how `.ipynb` *sources* render, not how toctree entries resolve.
The new tutorial's entry is a bare filename-stem line added to the existing `:::{toctree}`
block, e.g. `03_cli_walkthrough` (or whatever D-05's chosen filename is), same as
`01_full_pipeline`/`02_synthetic_validation` — no different syntax for `.md` vs `.ipynb`.

**`docs/conf.py` settings governing this** (`docs/conf.py:17-38`):
```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "nbsphinx",
    "sphinxcontrib.mermaid",
]
...
nbsphinx_execute = "never"  # Use committed outputs, don't re-execute
nbsphinx_allow_errors = False
nbsphinx_requirejs_path = ""  # Avoid RequireJS conflicts
...
myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
]
```
Markdown parser is **myst-parser** (not recommondmark) — `.md` tutorial page should use MyST
syntax throughout: `:::{admonition}`/`:::{toctree}` colon-fence directives (enabled via
`colon_fence`), `$...$`/`$$...$$` math (via `dollarmath`), and `{func}`/`{class}`/{mod}` cross-
reference roles exactly as seen in `configuration.md` and `optimizer.md` above.
`nbsphinx_execute = "never"` confirms D-21's "no re-execution" decision is already the sphinx-
build default and needs no change — it governs only the `.ipynb` files' cell-output rendering
and has no effect on the new `.md` page.

**Root nav entry precedent** (`docs/index.md:37-42`, `:58-67`): the Tutorials card and hidden
root toctree don't need a new top-level entry (tutorials/index.md is already the one linked
node); only `docs/tutorials/index.md`'s own toctree needs the new stem.

---

### `docs/tutorials/01_full_pipeline.ipynb` (notebook edits, D-18/D-20)

**Cell-by-cell map of what D-18 removes and D-20 must edit:**

| Cell | Type | Current text (verbatim, relevant excerpt) | Action |
|------|------|---------------------------------------------|--------|
| 0 | markdown | `"Run all four calibration stages (or load a previous calibration)"` (title cell, full text read above) | D-20: survives branch deletion but the "four calibration stages" / "load a previous calibration" framing should be reviewed against DOCS-06's three-stage framing (per CONTEXT D-20 note) |
| 2 | markdown | `"**`zenodo`**: Downloads a real hardware dataset from Zenodo (~164 MB, 13 cameras) and runs the full calibration pipeline from scratch. A reference calibration is included for comparison but is not used. Requires internet on first run. ..."` | D-18: **delete** this bullet entirely (whole zenodo option description dies with the branch) |
| 3 | code | `DATA_SOURCE = "zenodo"  # Options: "synthetic-small", "synthetic-large", "zenodo"` | D-18: change default to `"synthetic-small"` (or `"synthetic-large"`) and drop `"zenodo"` from the options comment |
| 6 | markdown | `"- **Zenodo (real rig)**: download the dataset and run the complete pipeline (Stages 1-4, ~15-20 min)"` | D-18: delete this bullet |
| 7 | code | `elif DATA_SOURCE == "zenodo": ... print("Running full calibration pipeline (Stages 1-4, ~15-20 min)...")` (full branch, `01_full_pipeline.ipynb` cell 7) | D-18: **delete the entire `elif DATA_SOURCE == "zenodo":` branch**, including its `load_example`/`run_calibration`/chdir logic; keep the `if DATA_SOURCE in ("synthetic-small", "synthetic-large"):` branch and the trailing `else: raise ValueError(...)` |
| 26 | markdown | `"1. Load calibration data (synthetic or real hardware from Zenodo)"` and `"2. Run the calibration pipeline (Stages 2-3 for synthetic, Stages 1-4 for real data)"` | D-20: reword — drop the Zenodo/Stages-1-4 half of both list items since only synthetic remains |

Outputs are stored as standard Jupyter cell `outputs` arrays inside the `.ipynb` JSON (executed
once, committed, never re-run by CI — consistent with `nbsphinx_execute = "never"`). Since the
notebook becomes synthetic-only and synthetic scenarios run in seconds, D-21's manual
re-execution after editing is cheap; no code pattern is needed for this beyond "run the notebook
top-to-bottom locally and save."

---

### `docs/tutorials/02_synthetic_validation.ipynb` (notebook edits, D-19/D-20)

**`RIG_SIZE` — exactly two sites, both confirmed on disk:**

Site 1, cell 2 (code), declaration + inline comment:
```python
# Toggle rig size:
#   "small" - 4 cameras, 20 frames, ideal conditions. Fast, ~2 min total.
#   "large" - 12 cameras, 30 frames, realistic noise. Compelling results, ~60 min total.
RIG_SIZE = "large"

OUTPUT_DIR = Path("output")  # exported data artifacts
```
Action: change `RIG_SIZE = "large"` to `RIG_SIZE = "small"` (D-19). The comment block above it
technically doesn't need to change (both toggle values are still explained), but D-20's full
editorial pass should confirm the "~60 min total" line is still accurate context now that
`"large"` is no longer the default — consider reordering so `"small"` (now default) is
described first, matching the convention in notebook 01 cell 2 where the recommended-first
option leads.

Site 2, cell 6 (code), branch condition:
```python
if RIG_SIZE == "small":
    # create_scenario("ideal"): 4 cameras at Z=0, water at the real-rig standoff
    ...
    SCENARIO_NAME = "ideal"
    ...
else:
    # create_scenario("realistic"): 12 cameras, water at ~1.03m, boards at 1.1-2.0m depth
    ...
    SCENARIO_NAME = "realistic"
    ...

print(f"RIG_SIZE = {RIG_SIZE!r}")
```
No code change needed here — the branch already handles both values; only the *default value*
set in cell 2 changes. This cell is included for completeness since CONTEXT.md's D-19 says
"`RIG_SIZE` appears in two places" and this is the second.

---

### `pyproject.toml` / `requirements.txt` (dependency pin, folded todo)

**Current lines to change:**
```
pyproject.toml:33:    "opencv-python>=4.6,<5.0",
requirements.txt:10:opencv-python>=4.6,<5.0
```
These are **already correctly pinned** (`<5.0` is present in both files as of this session) —
re-verify at plan time whether the folded todo
(`2026-08-05-pin-opencv-below-5-0.md`) is already satisfied or whether CONTEXT.md's framing
("unbounded above") is stale. If already pinned, this file entry may be a no-op verification
rather than an edit.

---

### `.pre-commit-config.yaml` (DATA-01b repo surgery)

**Current relevant hook config:**
```yaml
      - id: check-added-large-files
```
at line 16, with a scoped `exclude: ^experiments/results/` at line 25 that must be removed per
D-22 ("Claude's Discretion" section) once the five large artifacts are removed from
`experiments/results/`. A second, unrelated `exclude` at line 49 (notebook/experiments-results
formatting exclusion) is a different hook and is not in scope. Read the full hook block at plan
time before editing (only a partial grep was done here — this is a config edit, not a pattern
copy, so no further pattern excerpt is needed beyond locating the exact line).

## Shared Patterns

### MyST/Sphinx admonition conventions
**Source:** `docs/guide/configuration.md:109-118`, `docs/guide/refractive_geometry.md:105-127`
**Apply to:** `benchmarking.md`, the CLI tutorial `.md` page
```markdown
:::{admonition} <Title>
:class: warning|tip|note
<body>
:::
```
Use `warning` for "do not use this in production" caveats, `tip` for implementation rationale,
`note` for ablation/analysis-only callouts — this three-way class convention is consistent
across every guide page read.

### Reference-table + fenced-example pairing
**Source:** `docs/guide/configuration.md` (every `##` section)
**Apply to:** `benchmarking.md`
Every documented artifact section pairs a `| Key | Type | Default | Meaning |` (or equivalent)
table with an immediately-following fenced code block showing a real trimmed excerpt — never
table-only or example-only.

### Cross-reference roles
**Source:** `docs/guide/configuration.md:10`, `optimizer.md:46`
**Apply to:** all new/edited guide and tutorial pages
```markdown
{class}`aquacal.config.schema.CalibrationConfig`
{func}`aquacal.calibration.intrinsics.calibrate_intrinsics_all`
{mod}`aquacal.calibration._optim_common`
```
Standard Sphinx domain roles resolved by `sphinx.ext.autodoc` + `myst_parser`; use for every
first mention of a Python symbol being described in prose.

### `FrameSet`-compatible frame I/O
**Source:** `src/aquacal/io/frameset.py:11-33` (the `Protocol`), implemented by
`src/aquacal/io/video.py`'s `VideoSet` and `src/aquacal/io/images.py`'s `ImageSet`
**Apply to:** `scripts/<frame-extractor>.py`
The extractor should treat `VideoSet.iterate_frames(step=frame_step)` as the read side and
plain `cv2.imwrite(f"{camera_dir}/frame{idx:04d}.png", frame)` as the write side — both
directly reusable without modification (`ImageSet` on the read-back side requires no change
since `.png` is already in its accepted-extensions set).

### argparse `main()` script entry point
**Source:** `experiments/e2_real_rig.py:961-987` (trimmed to remove suite-specific
`--smoke`/`--check`/`--force` machinery, which does not apply to a non-experiment script)
**Apply to:** `scripts/<frame-extractor>.py`
```python
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    ...
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ...
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/<frame-extractor>.py` (script shape as a whole) | utility/script | batch, file-I/O | `scripts/` does not exist; no committed non-package runnable script exists anywhere in the repo. Nearest precedent (`experiments/e2_real_rig.py`) carries suite-specific machinery (`--smoke`/`--check`, resumable CSV writers, band-config emission) that is explicitly out of scope per D-11 — use only its bare argparse/`main()` skeleton, not its I/O helpers from `experiments/_io.py`. |
| `docs/tutorials/<cli-tutorial>.md` (as a `.md` tutorial specifically) | tutorial | batch | No existing `.md` page lives under `docs/tutorials/` — both current tutorials are `.ipynb`. `docs/guide/cli.md` supplies command-block conventions; notebook 01's markdown cells supply narrative/tutorial voice; neither is a full analog for a *written* (non-notebook) end-to-end walkthrough. |

## Metadata

**Analog search scope:** `docs/guide/*.md`, `docs/tutorials/*.md|*.ipynb`, `docs/index.md`,
`docs/conf.py`, `src/aquacal/io/*.py`, `src/aquacal/datasets/*.py`, `experiments/e2_real_rig.py`,
`experiments/_io.py`, `pyproject.toml`, `requirements.txt`, `.pre-commit-config.yaml`
**Files scanned:** ~20 read in full or targeted excerpt, plus directory listing of the staged
Zenodo archive mirror at `docs/tutorials/aquacal_data/real-rig/real-rig/extrinsic/`
**Pattern extraction date:** 2026-08-10
