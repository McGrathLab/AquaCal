---
phase: quick-260807-dcv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - experiments/e1_refractive_comparison.py
  - experiments/e7_interface_ablation.py
  - experiments/check_rerun_gates.py
  - tests/unit/test_e1_band_mode.py
  - tests/unit/test_e7_band_mode.py
  - tests/unit/test_rerun_gates.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "exp1_band.csv, when regenerated, carries z_rmse_mm per (seed, test_depth_m, model) — the quantity the manuscript's ~135x headline ratio is built from"
    - "A --seeds run of E1 writes e1_seed_band_provenance.json recording solver_config['seeds']"
    - "A --seeds run of E7 writes e7_seed_band_provenance.json recording solver_config['seeds']"
    - "gate4_band reads those band-owned sidecars and PASSes when their seed list matches the CSV's distinct seeds"
    - "The single-seed production records e1_benchmark_*.json / e7_benchmark_*.json are untouched by this change"
  artifacts:
    - path: "experiments/e1_refractive_comparison.py"
      provides: "band column merge + e1 band sidecar writer"
      contains: "e1_seed_band_provenance.json"
    - path: "experiments/e7_interface_ablation.py"
      provides: "e7 band sidecar writer"
      contains: "e7_seed_band_provenance.json"
    - path: "experiments/check_rerun_gates.py"
      provides: "gate4_band accepts band-owned sidecars"
      contains: "band_sidecar"
  key_links:
    - from: "experiments/e1_refractive_comparison.py::_run_band._runner"
      to: "_build_dataframes df_exp3"
      via: "1:1 merge on (test_depth_m, model)"
      pattern: "validate=\"one_to_one\""
    - from: "experiments/check_rerun_gates.py::run_all_gates"
      to: "check_band_csv"
      via: "band_sidecar= keyword"
      pattern: "seed_band_provenance"
---

<objective>
E1's committed band artifact does not contain the quantity the manuscript's headline number
is built from, and neither E1's nor E7's band can be verified against the seed list it claims
to cover.

**The z_rmse gap.** The abstract (`main.tex` L68) and §3 (L281) cite a ~135x
refractive-vs-non-refractive improvement. That is raw `z_rmse_mm` at the deepest test point
(2.5 m). `z_rmse_mm` exists only in `exp3_xy_vs_z_anisotropy.csv` (seed 42 alone, no `seed`
column) and in the gitignored `seed_sweep_19_3/`. So the published 10-seed band
(97.3x–178.0x, mean 139.5, n=10) is **not regenerable from any committed artifact**. E1's
`_run_band` already computes `df_exp3` every seed and throws it away.

**The sidecar gap.** `check_rerun_gates.py`'s `gate4_band` FAILs for both E1 and E7 with
"no sidecar matching 'eN_benchmark_*.json' records solver_config['seeds']". The committed
`e1_benchmark_*.json` / `e7_benchmark_*.json` are single-seed SEEDLESS_LEGACY_RECORDS, and
band mode must **not** overwrite them — doing so would replace the seed-42 production record
with the last band seed's values. Phase 19.5 already solved this shape for E5/E6 with a
band-owned sidecar; this plan copies that pattern to E1 and E7.

Purpose: make the published E1 band regenerable, and make both bands gate-verifiable.
Output: three modified experiment scripts and three modified test files. **No numeric,
solver, or calibration behaviour changes anywhere** — Task 1 is a pure output change over
values `_build_dataframes` already computes; Tasks 2 and 3 add a file and a lookup path.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md

Source files (read the named functions, not the whole file):
- `experiments/e1_refractive_comparison.py` — `_build_dataframes` (L312–448), `_run_band`
  (L687–794), column constants `EXP2_COLUMNS`/`EXP3_COLUMNS`/`EXP3_KEY_COLUMNS`/
  `BAND_KEY_COLUMNS` (L133–175)
- `experiments/e7_interface_ablation.py` — `_run_band` (L656–709)
- `experiments/check_rerun_gates.py` — `check_band_csv` (L677–790) and its two call sites
  (L1650–1653); `check_e6_seed_band` (L814+) is the phase-19.5 pattern to mirror
- `experiments/e6_generalization_sweep.py` L1101, L1144–1175 — the sidecar writer to copy
- `experiments/e5_index_sensitivity.py` L725–752 — the same writer with a `scope` string
- `experiments/_io.py::run_seed_band` (L166–217) — stamps the `seed` column onto whatever
  frame the runner returns, then concatenates
- `experiments/results/e6_seed_band_provenance.json` — the on-disk sidecar shape

<interfaces>
<!-- Contracts the executor needs. No codebase exploration required. -->

experiments/e1_refractive_comparison.py:
```python
EXP2_COLUMNS = ["test_depth_m", "model", "signed_mean_mm", "rmse_mm",
                "scale_factor", "calib_depth_min_m", "calib_depth_max_m"]
EXP3_COLUMNS = ["test_depth_m", "model", "xy_rmse_mm", "z_rmse_mm",
                "anisotropy_ratio", "n_points"]
EXP3_KEY_COLUMNS = ["test_depth_m", "model"]
BAND_KEY_COLUMNS = ["seed", "test_depth_m", "model"]
BENCHMARK_FILENAMES = {"refractive": "e1_benchmark_refractive.json",
                       "non_refractive": "e1_benchmark_nonrefractive.json"}

def _build_dataframes(scenario, results, seed, test_depths=None):
    ...  # returns (df_exp1, df_exp2, df_spatial, df_exp3)

def _run_band(seeds: list[int], out_dir: Path, smoke: bool, force: bool) -> None: ...
```

experiments/_io.py:
```python
def run_seed_band(runner: Callable[[int], pd.DataFrame],
                  seeds: Sequence[int]) -> pd.DataFrame: ...
```

aquacal.io:
```python
def capture_environment() -> dict  # git_sha, versions, cpu/ram; shells out to git rev-parse
```

experiments/check_rerun_gates.py:
```python
def check_band_csv(experiment: str, out_dir: Path, csv_name: str,
                   sidecar_glob: str) -> list[GateResult]: ...
```
</interfaces>
</context>

<hard_constraints>
The executor MUST obey all of these. They are not advisory.

1. **Do NOT run any band (`--seeds`) at production scale, and do NOT run the full test
   suite.** The orchestrator runs E1's ten-seed band (~70 min) after this code lands, and
   runs `pytest tests/` at the post-merge gate. An executor that launches a multi-hour job
   and returns has **stalled permanently** — see CLAUDE.md § "Never let a subagent background
   a long run and return". Allowed test commands, and nothing broader:
   - `python -m pytest tests/unit/test_e1_band_mode.py -v`
   - `python -m pytest tests/unit/test_e7_band_mode.py -v`
   - `python -m pytest tests/unit/test_rerun_gates.py -v`
   - `python -m pytest tests/unit/test_experiments_provenance.py -v` (read-only check that
     nothing was broken; do NOT edit that file)
   The existing `--smoke --seeds 42,43` tests in the band-mode files are the intended
   coverage vehicle — they run real calibrations at smoke scale and already pass today.

2. **Do NOT register any CSV in `CSV_TO_RECORD`** (`tests/unit/test_experiments_provenance.py`).
   `exp1_band.csv` is already registered and only gains columns. A new key naming a file not
   yet on disk fails `test_csv_to_record_has_no_stale_entries`. The orchestrator handles
   registration with the artifact commit.

3. **Expected residual failures — do NOT fudge them.** After this work `gate4_band` will
   STILL FAIL for both E1 and E7, because the band sidecars do not exist on disk until the
   bands are actually re-run. E7's stays FAILing until a re-run deliberately deferred past
   the Zenodo regeneration. Report these as expected in the SUMMARY. **Never weaken a gate,
   loosen a tolerance, or add an N/A branch to make them green.**

4. **Do NOT touch the `write_direct_call_benchmark` calls** in either `_run_band`
   (E1 L776–793, E7 L699–709) or their `force=force` argument. Those write the single-seed
   production records `e{1,7}_benchmark_*.json`, and the current non-forcing behaviour is
   what protects the seed-42 record. Adding `--force` to a band run is the WRONG fix.

5. **No numeric behaviour may change.** No calibration, solver, seed, scenario, tolerance,
   or existing column value. Task 1 merges two frames that `_build_dataframes` already
   returns. Tasks 2–3 add a file and a lookup order.

6. **Worktree note:** if working in a git worktree, `export PYTHONPATH="$(pwd)/src"` before
   running pytest. The editable install otherwise resolves `aquacal` to the MAIN checkout and
   the tests validate the wrong code (see CLAUDE.md).
</hard_constraints>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: E1's band CSV gains the anisotropy columns, including z_rmse_mm</name>
  <files>experiments/e1_refractive_comparison.py, tests/unit/test_e1_band_mode.py</files>
  <behavior>
    - `merge_band_columns(df_exp2, df_exp3)` returns a frame whose columns are exactly
      `BAND_MERGED_COLUMNS` (EXP2_COLUMNS then the four EXP3-only columns).
    - Row count is unchanged from `df_exp2` — the merge multiplies no rows.
    - Every EXP3 value lands on the row with the matching `(test_depth_m, model)`.
    - A duplicated key in either input raises (the `validate="one_to_one"` guard fires)
      rather than silently fanning out.
    - `n_points` survives as an integer dtype (full key coverage means no NaN promotion).
    - End to end: `main(["--smoke", "--seeds", "42,43", "--out", tmp])` writes an
      `exp1_band.csv` containing `xy_rmse_mm`, `z_rmse_mm`, `anisotropy_ratio`, `n_points`
      alongside every existing EXP2 column, with the row count still
      `n_seeds * n_depths * len(MODELS)` (4 at smoke scale — unchanged from today).
  </behavior>
  <action>
Add a module-level constant next to the other column constants (near L175):

`BAND_MERGED_COLUMNS = EXP2_COLUMNS + [c for c in EXP3_COLUMNS if c not in EXP2_COLUMNS]`

with a comment recording WHY it exists: the manuscript's headline ratio is raw `z_rmse_mm`
at the deepest test depth, which lived only in the seedless `exp3_xy_vs_z_anisotropy.csv`
and in gitignored sweep output, so the published band was not regenerable. Do NOT touch
`EXP2_COLUMNS` or `EXP3_COLUMNS` themselves — the single-seed CSVs they pin must stay
byte-identical.

Add a small pure helper, testable without running a calibration:

`def merge_band_columns(df_exp2: pd.DataFrame, df_exp3: pd.DataFrame) -> pd.DataFrame`

It performs `pd.merge(df_exp2, df_exp3, on=EXP3_KEY_COLUMNS, how="left",
validate="one_to_one")` and then reindexes the result to `BAND_MERGED_COLUMNS` so column
order is deterministic. Both inputs are (n_depths x n_models) per seed and share the same
`depths` list object inside `_build_dataframes`, so the float keys are identical objects —
state that in the docstring as the reason a float-keyed merge is safe here, and keep
`validate="one_to_one"` as the executable guard rather than a comment. Google-style
docstring; note that `seed` is NOT a merge key because `run_seed_band` stamps it after the
runner returns.

In `_run_band`'s inner `_runner` (L733–743), stop discarding `df_exp3`:
replace `_df_exp1, df_exp2, _df_spatial, _df_exp3 = _build_dataframes(...)` with a form that
binds `df_exp3`, and `return merge_band_columns(df_exp2, df_exp3)` instead of `return df_exp2`.
Nothing else in `_runner` changes — same scenario, same seeds, same `_run_one_model` calls.

Update `_run_band`'s docstring and the module docstring's "`--seeds` band mode" section
(L27–34): `exp1_band.csv` is now `exp2_depth_generalization.csv`'s columns PLUS
`exp3_xy_vs_z_anisotropy.csv`'s four non-key columns PLUS `seed`. Say explicitly that this
GAINS COLUMNS on an existing artifact rather than adding a sibling file, and that
`exp3_xy_vs_z_anisotropy.csv` itself is still written only by the single-seed run.

Add tests to `tests/unit/test_e1_band_mode.py` covering the `<behavior>` list. Put the pure
`merge_band_columns` cases in a new `TestMergeBandColumns` class built from small hand-made
DataFrames (no calibration, instant), and extend `TestBandMode.test_band_csv_written_at_smoke_scale`
(or add a sibling test) for the end-to-end column assertion. Keep the existing assertion
`set(df.columns) >= set(EXP2_COLUMNS)` valid — it still holds.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/test_e1_band_mode.py -v</automated>
  </verify>
  <done>`exp1_band.csv` produced by a smoke band carries all four EXP3 columns; row count per
  seed is unchanged; the pure merge helper is unit-tested including the duplicate-key guard;
  no EXP2/EXP3 constant changed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: band-owned provenance sidecars for E1 and E7</name>
  <files>experiments/e1_refractive_comparison.py, experiments/e7_interface_ablation.py, tests/unit/test_e1_band_mode.py, tests/unit/test_e7_band_mode.py</files>
  <behavior>
    - `main(["--smoke", "--seeds", "42,43", "--out", tmp])` on E1 writes
      `tmp/e1_seed_band_provenance.json` with `solver_config["seeds"] == [42, 43]`,
      `experiment == "e1_seed_band"`, `schema_version == 1`, a non-empty `git_sha`, a
      numeric `seconds`, an `environment` dict, and a non-empty `scope` string.
    - Same for E7 → `tmp/e7_seed_band_provenance.json`, `experiment == "e7_seed_band"`.
    - The existing `e{1,7}_benchmark_*.json` writes are unaffected: they still appear and
      still carry `solver_config["seeds"]` (the existing tests asserting this keep passing).
    - A plain single-seed run (`--smoke` without `--seeds`) writes NO band sidecar.
    - `experiments/results/` is untouched by any of these runs (the existing
      `test_no_results_dir_modified` guard still passes).
  </behavior>
  <action>
Mirror `e6_generalization_sweep._run_band`'s sidecar writer (L1101, L1144–1175) and
`e5_index_sensitivity`'s `scope` field (L738–750). Same key set, same
`json.dump(..., indent=2, sort_keys=True)`, same `print(f"Wrote {path}")` convention.

**E1** (`experiments/e1_refractive_comparison.py`): add `import json` and `import time` to
the stdlib block (L77–80) and `from aquacal.io import capture_environment` to the aquacal
import block. In `_run_band`, capture `environment = capture_environment()` and
`start = time.monotonic()` before the seed loop, compute `elapsed_seconds` right after
`run_seed_band` returns, and after the `write_experiment_csv` call write
`out_dir / "e1_seed_band_provenance.json"` with:
`experiment: "e1_seed_band"`, `schema_version: 1`, `git_sha: environment.get("git_sha")`,
`seconds`, `environment`, `solver_config: {"seeds": list(seeds)}`, `scope`.
Capture the environment ONCE, before the loop — `capture_environment()` shells out to
`git rev-parse` per call, and a per-cell call is what split an artifact's recorded SHA
before (CLAUDE.md / knowledge-base).

E1's `scope` string must state what varies and what it bounds: the SEED varies across E1's
depth-generalization and xy-vs-z anisotropy sweep on the `"realistic"` synthetic scenario;
the band bounds seed-to-seed variance of those metrics on that synthetic scenario only —
not a physical-rig or real-data claim. Name `z_rmse_mm` explicitly as the column the
manuscript's deepest-test-point refractive-vs-non-refractive ratio is computed from, and
say the band exists so that ratio is regenerable from a committed artifact. State the
bounds; do not assert or deny an accuracy claim in the sidecar text.

**E7** (`experiments/e7_interface_ablation.py`): `json` and `time` are already imported;
add `from aquacal.io import capture_environment`. Same shape in `_run_band`, writing
`out_dir / "e7_seed_band_provenance.json"` with `experiment: "e7_seed_band"`. E7's `scope`:
the SEED varies across the four fixed/refined x shared/per-camera arms; the band bounds
seed-to-seed variability of `camera_height_drift_mm`, the per-arm pairing behind MF-05.
**E7's CSV already carries its claim quantity — do NOT add or reorder any column in
`ABLATION_COLUMNS` or `interface_ablation_band.csv`.** E7 gains the sidecar only.

For both: the sidecar write goes AFTER the band CSV write and BEFORE (or after — but
independent of) the `write_direct_call_benchmark` loop, and is unconditional (no `force`
gate — it is band-owned, like the band CSV, and regenerating it is the point). Update each
`_run_band` docstring and each module's "`--seeds` band mode" docstring section to name the
new file and to state plainly that it exists because the single-seed
`e{1,7}_benchmark_*.json` records are seedless legacy records that band mode must never
overwrite.

Add tests to `tests/unit/test_e1_band_mode.py` and `tests/unit/test_e7_band_mode.py`
covering the `<behavior>` list, reusing each file's existing `--smoke --seeds 42,43` +
`tmp_path` pattern.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/test_e1_band_mode.py tests/unit/test_e7_band_mode.py -v</automated>
  </verify>
  <done>Both band sidecars are written by their `_run_band` with the E5/E6 key set and a
  scope string; the single-seed benchmark records and their `force` semantics are byte-for-byte
  unchanged in the source; a non-band run writes no sidecar.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: gate4_band reads the band-owned sidecars</name>
  <files>experiments/check_rerun_gates.py, tests/unit/test_rerun_gates.py</files>
  <behavior>
    - Band CSV with distinct seeds {42,43} + `e1_seed_band_provenance.json` recording
      `[42, 43]` → PASS, and the message names `e1_seed_band_provenance.json`.
    - Same for E7 / `e7_seed_band_provenance.json`.
    - Band sidecar present but recording a different-length seed list → FAIL with the
      existing "a partial band must never be quoted as a full one" text.
    - Band sidecar absent, legacy `e1_benchmark_*.json` present WITH a `seeds` list → PASS
      (backwards compatible; the fallback still works).
    - No sidecar of either kind → FAIL with the EXISTING text, still interpolating the
      `eN_benchmark_*.json` glob verbatim.
    - Band CSV absent → N/A, unchanged.
  </behavior>
  <action>
In `check_band_csv`, add a keyword parameter `band_sidecar: str | None = None` (an exact
filename, not a glob). Build the search order as a list of patterns — `band_sidecar` first
when given, then `sidecar_glob` — and run the existing `out_dir.glob(pattern)` /
`solver_config["seeds"]` extraction loop over that list, keeping the first hit. An exact
filename passed to `Path.glob` matches the single file, so no second code path is needed.

**Preserve the no-sidecar FAIL message verbatim**, interpolating `sidecar_glob` exactly as
today — constraint 3 above depends on that text staying stable, and `test_rerun_gates.py`
asserts against it. Extend the docstring's Verdicts block to say the band-owned sidecar is
preferred and the `eN_benchmark_*.json` glob is the legacy fallback, and record WHY the
band-owned file had to exist: band mode must never overwrite the single-seed production
record, so the seeds it ran had nowhere to be recorded.

At the two call sites (L1650–1653) pass
`band_sidecar="e7_seed_band_provenance.json"` and `band_sidecar="e1_seed_band_provenance.json"`
respectively. Change nothing else in `run_all_gates`.

Add tests to `tests/unit/test_rerun_gates.py` covering the `<behavior>` list, following
that file's existing fixture style for synthesising a `tmp_path` out_dir with a band CSV
and JSON sidecars. Do not modify or relax any existing gate assertion.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/test_rerun_gates.py -v</automated>
  </verify>
  <done>`gate4_band` PASSes for E1 and E7 against a synthetic band-owned sidecar; the legacy
  glob fallback still PASSes; the no-sidecar FAIL text is byte-identical to before; no
  existing gate test was changed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| filesystem writes under `--out` | The only new external effect: two additional JSON files |
| `capture_environment()` → `git rev-parse` | Existing subprocess call, reused unchanged |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-dcv-01 | Tampering | `e{1,7}_benchmark_*.json` production records | mitigate | Constraint 4: the `write_direct_call_benchmark` calls and their `force=force` are not touched; band sidecars are separate files. Tested by the existing benchmark assertions still passing. |
| T-dcv-02 | Repudiation | band provenance | mitigate | Sidecar records `git_sha`, `seeds`, `environment` and `seconds`, captured ONCE per band so a run cannot straddle two SHAs |
| T-dcv-03 | Tampering | committed `experiments/results/` | mitigate | All tests run against `tmp_path`; the existing `test_no_results_dir_modified` git-status guard stays in force |
| T-dcv-04 | Information disclosure | none | accept | No secrets, no network, local synthetic data only |
| T-dcv-SC | Tampering | package installs | N/A | This plan installs no packages; every import is already a project dependency |
</threat_model>

<verification>
Targeted only — the orchestrator owns the full suite (constraint 1):

```bash
python -m pytest tests/unit/test_e1_band_mode.py tests/unit/test_e7_band_mode.py tests/unit/test_rerun_gates.py -v
python -m pytest tests/unit/test_experiments_provenance.py -v   # read-only; do not edit
```

Source-level checks (no run required):

```bash
grep -c "force=force" experiments/e1_refractive_comparison.py   # unchanged from pre-edit count
git diff -- experiments/e1_refractive_comparison.py | grep -E "^[-+].*write_direct_call_benchmark"  # expect no output
```
</verification>

<success_criteria>
- [ ] `exp1_band.csv` regenerated at smoke scale carries `xy_rmse_mm`, `z_rmse_mm`,
      `anisotropy_ratio`, `n_points` with no row multiplication
- [ ] `merge_band_columns` is unit-tested pure, including its `one_to_one` guard
- [ ] E1's `_run_band` writes `e1_seed_band_provenance.json`; E7's writes
      `e7_seed_band_provenance.json`; both record `solver_config["seeds"]` and a `git_sha`
- [ ] E7's CSV columns are unchanged
- [ ] `gate4_band` PASSes against a band-owned sidecar for both experiments; the legacy
      fallback and the no-sidecar FAIL text are both preserved
- [ ] No calibration, solver, seed, tolerance or existing column value changed
- [ ] No entry added to `CSV_TO_RECORD`
- [ ] No band and no full suite was run by the executor
- [ ] SUMMARY records that `gate4_band` still FAILs for E1 and E7 on disk (sidecars do not
      exist until the bands are re-run) and that this is EXPECTED, not a regression
</success_criteria>

<output>
Create `.planning/quick/260807-dcv-e1-e7-band-provenance-emit-z-rmse-column/260807-dcv-SUMMARY.md` when done
</output>
</content>
</invoke>
