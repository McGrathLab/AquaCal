# Phase 27: Frozen Single-Sha Handoff Package - Pattern Map

**Mapped:** 2026-08-19
**Files analyzed:** 13 (7 modified, 4 new, 2 process-only)
**Analogs found:** 11 / 11 code+doc files (2 process steps carry no file)

This is a scientific Python + Bash repository. There are no controllers, components or
middleware; the roles below are the ones this repo actually has: **suite driver (Bash)**,
**expectation manifest (JSON)**, **gate checker (Python)**, **experiment script (Python)**,
**provenance emitter (Python)**, **calibration config (YAML)**, **in-repo note (Markdown)**,
**driver test (Python/pytest-over-subprocess)**.

**The single strongest observation in this map:** almost every Phase 27 change has a
**self-analog** — the same file already contains the exact pattern the change must follow.
`GATE_PYTHON` already has a detect-then-fallback block. `_preflight_frameset` already reads
its expected numbers from the manifest. `run_one_stage` already reads per-stage attributes
from `STAGE_CONCURRENCY`. Prefer the in-file precedent over anything imported from elsewhere.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `experiments/run_experiment_suite.sh` (MOD, D-10/D-12/D-14/D-22) | suite driver (Bash) | batch / process-orchestration | itself — `:402-406`, `:928-1010`, `:672-678`, `:1808-1874` | exact (self-analog) |
| `experiments/suite_expectations.json` (MOD, D-20 + possibly D-10) | expectation manifest (JSON data) | declarative config | itself — existing `benchmark_grid.csv` entry is already `full`-only | exact (self-analog) |
| `experiments/EXPECTATIONS.md` (MOD, generated §7) | generated doc region | transform (JSON -> MD) | `experiments/render_expectation_sheet.py --write` | exact — **mandatory consequence of any manifest edit** |
| `experiments/check_rerun_gates.py` (MOD, D-20 class 2) | gate checker | batch validation -> `GateResult` list | `check_completeness` in `experiments/_expectations.py:191-196` (the only profile-aware checker today) | role-match |
| `experiments/reconstruction_bootstrap.py` (MOD, D-23) | experiment script | file-I/O, post-hoc re-analysis | `experiments/e4_benchmark_grid.py:296-309` (`out_dir /` then graceful fallback) | exact |
| `experiments/_run_manifest.py` (MOD, D-14 two-regime record) | provenance emitter | one-shot capture -> JSON | itself — `build_run_manifest():199-237` | exact (self-analog) |
| **NEW** environment lockfile emitter (D-13) | provenance emitter | subprocess capture -> text file | `experiments/_run_manifest.py` (whole module: argparse `--out`, `write_*`, never-raise) | exact |
| **NEW** `experiments/configs/<name>.yaml` — Linux E2 release config (D-11) | calibration config (YAML) | declarative config | `aquacal_data/real-rig/real-rig/config_paper.yaml` | **exact — image dirs, `frame_step: 1`, `max_calibration_frames: 200`, 13 extrinsic paths** |
| **NEW** emitter-coverage report (D-16, Markdown) | in-repo note | report | `experiments/EXPECTATIONS.md` | exact |
| **NEW** frozen-row classification note (D-19, Markdown) | in-repo note | report | `experiments/EXPECTATIONS.md` §2/§3 (pre-declared-mismatch tables) | exact |
| `tests/unit/test_run_experiment_suite_dryrun.py` (MOD) | driver test | subprocess-over-fixture | itself — `TestResume:479-527` | exact (self-analog) |
| `tests/unit/test_expectations.py` (MOD, D-20) | manifest test | data assertion | `TestProfiles:195-263` | exact |
| Push branch + annotated tag (D-01/D-02/D-03) | process step | — | `_VERSION_TAG_GLOB` note at `_run_manifest.py:104-108` (the repo already carries non-`v*` tags: `pre-rerun-baseline`) | n/a — no file |

---

## Pattern Assignments

### `experiments/run_experiment_suite.sh` — D-10 (path-kind-agnostic pre-flight)

**Analog:** itself, `_preflight_frameset` at `:913-1010`.

The embedded Python heredoc is the whole contract. **Preserve every `sys.exit` code and every
`print` prefix** — the Bash `case "${probe_exit}"` at `:1010+` branches on 0/2/3 and each branch
prints its own override flag (P26-D-50).

Manifest-read pattern to keep verbatim (`:929-940`) — this is why `min_total_bytes` must never
become a shell literal:

```python
manifest = json.loads(
    pathlib.Path("experiments/suite_expectations.json").read_text(encoding="utf-8")
)
frameset = manifest["preflight"]["frameset"]
cheap = frameset["cheap_check"]
```

The exact three lines D-09 identifies (`:955-958`):

```python
declared = config.get("paths", {}).get("extrinsic_videos", {}) or {}
paths = [pathlib.Path(p) for p in declared.values()]
present = [p for p in paths if p.is_file()]      # <-- False for every directory
total_bytes = sum(p.stat().st_size for p in present)   # <-- directory st_size is meaningless
```

D-10's shape: `p.exists()` for `present`, and a recursive byte sum for `total_bytes`
(`sum(f.stat().st_size for f in p.rglob("*") if f.is_file())` when `p.is_dir()`, else
`p.stat().st_size`). Everything else — the two assertions, the `expected_n` / `min_bytes` reads,
the `retired_signature` message, the three exits — is unchanged.

The exit-code / override coupling that must survive (`:1010+`, abbreviated):

```bash
  case "${probe_exit}" in
    0) log "preflight: E2 frameset identity check PASSED."; return 0 ;;
    2) # ABSENT -> --skip-e2 (DECLARES a synthetic-only run, writes the reduction marker)
    3) # MISMATCH -> --allow-frameset-mismatch
```

Override vocabulary is already fixed in the manifest at `preflight.overrides` — five entries.
**Do not add a sixth** (D-10 explicitly reuses; § D cut three refusals and no fourth is added).

---

### `experiments/run_experiment_suite.sh` — D-12 (two Windows literals)

**Analog:** itself, `:402-406`. **The detect-then-fallback pattern already exists** for
`GATE_PYTHON` — D-12 widens the chain, it does not invent one:

```bash
GATE_PYTHON="${PRELAUNCH_GATE_PYTHON:-$HOME/anaconda3/envs/AquaCal/python.exe}"
if [ ! -x "${GATE_PYTHON}" ] && ! command -v "${GATE_PYTHON}" >/dev/null 2>&1; then
  echo "WARNING: pinned gate interpreter not found at ${GATE_PYTHON}; falling back to bare 'python'. Gate verdicts may fail to import pandas." >&2
  GATE_PYTHON="python"
fi
```

Copy this exactly: env override first, probe with `[ -x ]` **and** `command -v`, warn to stderr
naming what was tried, then degrade. D-12 adds the middle rung (a conda env named `AquaCal` on
either platform, i.e. also `.../envs/AquaCal/bin/python`) and requires the resolution to be
**printed loudly on success too**, not only on failure.

`E2_RELEASE_CONFIG` (`:374`) already carries the override-variable idiom and a comment naming
Phase 27 as the repointer:

```bash
E2_RELEASE_CONFIG="${SUITE_E2_RELEASE_CONFIG:-C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml}"
```

D-12 swaps only the default to the newly committed in-repo path; the `SUITE_E2_RELEASE_CONFIG`
name stays (it is already threaded into the pre-flight heredoc's env at `:928`). Sibling
precedent for "default is in-repo, env var repoints" is `BASELINE_DIR` at `:392`.

---

### `experiments/run_experiment_suite.sh` — D-14 (thread pin, concurrent stages only)

**Analog:** `run_one_stage` at `:1808-1874`, plus `_load_stage_attributes` at `:1884-1934`.

The manifest already supplies the discriminator; nothing is hardcoded. Read pattern
(`:1884-1922`) — a one-shot Python call emitting TSV into a `while IFS=$'\t' read`:

```bash
  while IFS=$'\t' read -r name deps conc frame est; do
    STAGE_DEPS["${name}"]="${deps}"
    STAGE_CONCURRENCY["${name}"]="${conc}"
    ...
  done < <("${GATE_PYTHON}" - <<'PY'
```

Consumption pattern the pool already uses (`:2008`, `:2040`):

```bash
  [ "${STAGE_CONCURRENCY[${name}]}" = "serial_alone" ] && serial_running=1
```

**Insertion point for the pin** is the dispatch line in `run_one_stage` (`:1831`), which is a
single bare call and therefore the one place both the serial path and the pool path pass through:

```bash
  state_start "${name}" "${idx}"
  log ">>> STAGE ${idx}/${#STAGES[@]}: ${name} starting"

  "run_stage_${name}"          # <-- D-14 wraps this: export the cap only when
  local exit_code=$?           #     STAGE_CONCURRENCY[name] == "concurrent"
```

Use a subshell or an explicit unset around it so `e4`, `e4_repeat`, `e2_timing`, `e2_memory`
(the four `serial_alone` stages, pinned by `test_expectations.py::test_serial_alone_is_exactly_the_four_timing_stages`)
see **no** `OMP_NUM_THREADS` / `MKL_NUM_THREADS` / `OPENBLAS_NUM_THREADS` at all — an exported
empty string is not the same as unset to OpenBLAS.

**The manifest record half of D-14** goes in `experiments/_run_manifest.py` — see below.

---

### `experiments/run_experiment_suite.sh` — D-22 (`is_stage_complete` ignores the exit column)

**Analog:** itself. The defect and its fix are two adjacent functions.

The reader (`:672-678`) — note it tests `$3` and never `$5`:

```bash
is_stage_complete() {
  # A stage counts as complete only if the state file carries a "complete"
  # event line for it -- a start-only line (started, then died) never matches.
  local name="$1"
  [ -f "${STATE_FILE}" ] || return 1
  awk -F'\t' -v stage="${name}" '$1 == stage && $3 == "complete" { found = 1 } END { exit !found }' "${STATE_FILE}"
}
```

The writer (`:702-705`) — column 5 is the exit code, and it is always written:

```bash
state_complete() {
  local name="$1" idx="$2" exit_code="$3"
  printf '%s\t%s\tcomplete\t%s\t%s\n' "${name}" "${idx}" "$(date -u +"${STATE_TIME_FMT}")" "${exit_code}" >>"${STATE_FILE}"
}
```

Live proof from the frozen run's own state file
(`experiments/run_experiment_suite_state.88512b7.tsv`) — a stage that ran and **failed** and
today would be silently skipped on resume:

```
reconstruction_bootstrap	10	complete	2026-08-19T03:23:44.921Z	1
```

D-22 is `&& $5 == 0` added to the awk predicate. Keep the comment in step with the code — the
existing comment describes only the start-only case, and it becomes wrong the moment `$5` is read.

---

### `experiments/suite_expectations.json` — D-20 (retag artifacts) and D-24 (verify only)

**Analog:** the manifest's own `benchmark_grid.csv` entry, which is **already** `full`-only and
carries the rationale in prose:

```json
{
 "name": "benchmark_grid.csv",
 "dir": "experiments/results",
 "stage": "e4",
 "profiles": ["full"],
 "rows": {"full": 10},
 "rows_rationale": "9 synthetic cells + 1 real-rig row. The real-rig row is present ONLY if E2's production run wrote experiments/results/benchmark.json first ...",
 ...
}
```

Wait — this entry is already `["full"]`, which means **D-20's class 3 may already be satisfied.
Verify before editing.** The three class-1 entries are not:

```json
{"name": "structural_scaling.csv", "stage": "e3",         "profiles": ["smoke","full"], "rows": {"full": 84}}
{"name": "e5_provenance.json",     "stage": "e5",         "profiles": ["smoke","full"], "rows": {}}
{"name": "fd_jacobian_accuracy.json","stage":"fd_jacobian","profiles": ["smoke","full"], "rows": {}}
```

The retag is a one-token edit per entry (`["smoke","full"]` -> `["full"]`). **Also record WHY**
in the entry, following the house style above — every `rows_rationale` / `notes` field in this
file states the reason a number or tag is what it is, and D-20's reason is a code location
(`e3_derived_quantities.py:1106-1126` returns before `_write_tier4`).

**Consumer that makes the tag load-bearing** — `experiments/_expectations.py:191-196`:

```python
    for artifact in data["artifacts"]:
        if profile not in artifact["profiles"]:
            continue
        if stage is not None and artifact["stage"] != stage:
            continue
        results.append(_check_artifact(out_dir, artifact, profile, gate_result))
```

**D-24 (verify, do not build)** reads the same list. The two Phase 25 artifacts are present and
already correctly shaped — both `"profiles": ["full"]`, both `"conditional": true`, with the
conditional-emission rule stated in `rows_rationale`:

```json
{"name": "degenerate_observations.csv", "stage": "e2_production", "profiles": ["full"], "conditional": true,
 "rows_rationale": "written ONLY when at least one flagged row exists, so a clean run legitimately produces no file and its absence is PASS, not FAIL (Phase 25 D-08). ..."}
{"name": "all_observation_depths.csv",  "stage": "e2_production", "profiles": ["full"], "conditional": true,
 "rows_rationale": "written ONLY when internals.log_all_observation_depths is true, ... Absence is PASS. Expect about 11 MB on the 13-camera rig."}
```

The `conditional` flag's PASS path is `_expectations.py:212-222`. D-24's deliverable is a stated
finding, not an edit.

---

### `experiments/EXPECTATIONS.md` — the mandatory consequence of any manifest edit

**This is not optional and is easy to miss.** §7 of `EXPECTATIONS.md` is a generated region
rendered from `suite_expectations.json`, and a unit test fails when the two drift:

```markdown
§7 below is delimited by a pair of generated-region HTML comment markers, and everything between
them is rendered from `experiments/suite_expectations.json` by
`experiments/render_expectation_sheet.py`; `tests/unit/test_expectations.py -k sheet` fails when
the two drift apart. Everything outside those markers -- §§1-6 -- is hand-written, and the renderer
never touches it. Regenerate with:

    python -m experiments.render_expectation_sheet --write
    python -m experiments.render_expectation_sheet --check   # exits 1 if stale
```

The renderer reads `profiles` directly (`render_expectation_sheet.py:81`, `:121`, `:136`), so a
D-20 retag moves the rendered counts ("62 expected under the `full` profile"). **Every plan that
edits the manifest must end with `--write` and a `--check`.**

---

### `experiments/check_rerun_gates.py` — D-20 class 2 (E6 optimality + cameras axis at smoke scale)

**Analog:** `experiments/_expectations.py:153-197` — the only profile-aware checker in the
codebase, and the shape to imitate: `profile` is a **keyword-only** argument, validated against
the module-level `PROFILES` tuple, raising `ValueError` naming the offender.

Today no per-experiment checker takes a profile — `run_all_gates` (`:1997-2044`) calls them all
positionally, and only threads `profile` into the last call:

```python
    results += check_e6(out_dir)
    ...
    results += check_e6_seed_band(out_dir)
    ...
    if profile is not None:
        results += check_completeness(out_dir, profile=profile, stage=stage)
```

**Two distinct call sites carry the 5 failures.** Do not conflate them:

1. **`gate4_optimality` on `e6_configs/*.json`** — emitted by `check_e6` at `:758-789` via
   `_check_json_artifact(..., check_optimality=True)`. The existing flag is already the seam:

```python
    for config_path in config_paths:
        record = _load_json(config_path)
        label = f"e6_configs/{config_path.name}"
        results += _check_json_artifact(
            "E6", label, record,
            check_guard=True,
            check_optimality=True,          # <-- becomes profile-dependent
            require_water_index=True,
        )
```

   The smoke remedy is `check_optimality=(profile != "smoke")`, which needs `profile` threaded
   through `check_e6`'s signature and `run_all_gates`'s call. `_check_json_artifact` itself needs
   no change — it already gates every optimality verdict behind that boolean.

2. **`cameras axis missing [12, 16]; found [8]`** — `check_e6_seed_band` at `:1079-1109`, against
   a module constant that is deliberately NOT manifest-derived:

```python
# NOT derived from the manifest and NOT changed: the `cameras` axis survives D-40.
_E6_EXPECTED_CAMERA_VALUES = (8, 12, 16)
...
        missing = [v for v in _E6_EXPECTED_CAMERA_VALUES if v not in cameras_values]
        if missing:
            results.append(
                GateResult("E6", "gate_e6_seed_band:cameras_axis", "FAIL",
                    f"cameras axis missing value(s) {missing}; found {cameras_values}")
            )
```

   Make the **expectation** profile-dependent, not the constant: at smoke, assert the axis column
   exists and emit PASS (or `"N/A"`) naming the collapsed scale. `GateResult.verdict` is
   `"PASS" | "FAIL" | "N/A"` (`:92-107`) and `"N/A"` is the established verdict for
   "this artifact's stage has not run at production shape" — see `check_e6_seed_band:1000-1008`.

**Contract to preserve (from CONTEXT § Reusable Assets):** keep emitting `GateResult`s so the
verdict-block formatting in `main()` is unchanged. Do not introduce a second result type — the
late-import dance in `_expectations.py:50-61` exists precisely to avoid that.

Test analog: `tests/unit/test_rerun_gates.py::TestCheckE6SeedBand` (`:1067`) and
`::TestGate4Optimality` (`:550`).

---

### `experiments/reconstruction_bootstrap.py` — D-23 (hardcoded output path)

**Analog:** `experiments/e4_benchmark_grid.py:296-309` — the repo's canonical
"resolve a companion artifact from `--out`, degrade honestly if absent" block:

```python
    out_dir = Path(out_dir)
    candidate = out_dir / "benchmark.json"
    if candidate.exists():
        return candidate, "native: resolved relative to --out"
    if out_dir.resolve() == E2_BENCHMARK_PATH.parent:
        return E2_BENCHMARK_PATH, "default tree: __file__-anchored E2_BENCHMARK_PATH"
    return (
        None,
        f"absent: no benchmark.json under {out_dir} and --out is not the default "
        f"tree; refusing to import {E2_BENCHMARK_PATH}, which describes a "
        "different machine's run",
    )
```

The defect (`:56`, `:222-224`) — a module-level constant read by a function that takes no
`out_dir` at all:

```python
REAL_RIG_METRICS_PATH = Path("experiments/results/real_rig_metrics.json")
...
def _load_real_rig_metrics() -> dict:
    with open(REAL_RIG_METRICS_PATH) as f:
        return json.load(f)
```

`_run(seed, n_resamples, errors_path)` calls it; `main` already has the resolved directory:

```python
    out_dir = resolve_out_dir(args.out)
    path = out_dir / "reconstruction_bootstrap.json"
```

Thread `out_dir` into `_run` and `_load_real_rig_metrics`, resolve `out_dir / "real_rig_metrics.json"`
first. Two secondary patterns to honour:

- **The `__file__`-anchored fallback**, not a cwd-relative one — `e5_index_sensitivity.py:656-676`
  documents exactly why (`_default_metrics_path`: "a cwd-relative miss degrades both to null with
  only a WARNING ... a silently degraded artifact of exactly the kind this phase exists to
  eliminate").
- **Do not let absence become a silent `False`.** The consumed value feeds
  `point_estimate_matches_real_rig_metrics` (`:250-256`), which the `--check` path then reports as
  a mismatch (`:334-336`). Under `--smoke` an absent companion should be honestly `None`/skipped,
  not a false negative.

Also mirror the existing three-branch resolver in this same file
(`resolve_reconstruction_errors_path`, `:180-215`) — explicit flag, then local, then archive,
with a `FileNotFoundError` message that enumerates all three places it looked.

---

### `experiments/_run_manifest.py` — D-13 (lockfile) and D-14 (two-regime thread record)

**Analog:** itself. `build_run_manifest()` (`:199-237`) is a flat dict assembled over
`capture_environment()` plus the four things it cannot record:

```python
    env = capture_environment()
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "git_sha": env.get("git_sha"),
        "git_describe": _resolve_git_describe(),
        "git_dirty": _resolve_git_dirty(),
        ...
        "opencv_build": _resolve_opencv_build(),
        # F-002: the last BUILT version, never "the code that ran".
        "installed_distribution_version": _resolve_installed_distribution_version(),
        "utc_start": _utc_now_iso_z(),
    }
```

**D-14's record** is two new keys of this shape — the cap value and the stage list it applied to
(read from the manifest's `concurrency` attribute, never a second hardcoded list). Adding keys is
safe: the gate imports `REQUIRED_MANIFEST_FIELDS` (`:75-93`) and checks presence of those names
only, so new fields do not break `_check_run_manifest` (`check_rerun_gates.py:1824`) — but keep
the "any unavailable source is `None`, never absent" rule stated at `:207-211`.

**D-13's lockfile emitter** copies this module wholesale as a template:

- never-raise subprocess helper — `_run_git` (`:113-135`): `capture_output=True, text=True,
  check=False`, `except (OSError, ValueError)`, `return None` on any failure, `logger.debug` the
  reason. `pip freeze` gets the same treatment.
- writer with the FileExistsError guard and explicit `--force` — `write_run_manifest`
  (`:240-271`): `out_dir.mkdir(parents=True, exist_ok=True)`, `path = out_dir / FILENAME`,
  refuse on exists-without-force with a message naming the decision.
- `build_arg_parser` with `--out` **required** and `--force` (`:274-294`), `main()` returning
  0/1 and printing `Wrote ...: {path}` (`:297-311`).

**Driver call site to copy** — `run_stage_preflight` at `:864-875`. Note it passes `--force`
deliberately and turns a non-zero exit into a refusal with **no** override:

```bash
  log "preflight: writing the suite run manifest into ${OUT_DIR}"
  "${GATE_PYTHON}" -m experiments._run_manifest --out "${OUT_DIR}" --force
  local manifest_exit=$?
  if [ "${manifest_exit}" -ne 0 ]; then
    log "PREFLIGHT REFUSAL: the run manifest could not be written (exit=${manifest_exit}). ... There is NO override for this refusal ..."
    return "${manifest_exit}"
  fi
```

**Caution:** D-13's lockfile is an *artifact*, not a refusal. Phase 26 § D cut three pre-flight
refusals and P26-D-50 binds every survivor to print an override flag. A failed `pip freeze` must
log and continue — do **not** copy the hard-abort half of the block above.

---

### NEW — the committed Linux E2 release config (D-11)

**Analog:** `aquacal_data/real-rig/real-rig/config_paper.yaml` — an exact structural match. It
already points at **image directories** (not videos), already sets both D-11 values, and already
declares 13 extrinsic paths (12 main + 1 auxiliary), which is exactly
`cheap_check.n_extrinsic_videos: 13`.

```yaml
cameras:
- e3v829d
  ... (12 total)
auxiliary_cameras:
- e3v8250
fisheye_cameras:
- e3v8250
paths:
  intrinsic_videos:
    e3v8250: intrinsic/e3v8250/
    ... (13 entries, all DIRECTORIES with a trailing slash)
  extrinsic_videos:
    e3v8250: extrinsic/e3v8250/
    ... (13 entries)
  output_dir: output
interface:
  n_air: 1.0
  n_water: 1.333
  normal_fixed: false
  initial_water_z:
    e3v829d: 1.0
    ... (one per camera, 13 entries)
optimization:
  robust_loss: huber
  loss_scale: 1.0
  max_calibration_frames: 200      # D-11
  refine_intrinsics: true
  refine_auxiliary_intrinsics: true
detection:
  min_corners: 8
  min_cameras: 2
  frame_step: 1                    # D-11 -- NOT the Desktop config's 30
validation:
  holdout_fraction: 0.2
  save_detailed_residuals: true
```

Its header comment is also the right precedent for the new file's — it states the frame-step
reasoning explicitly, which is the discrepancy D-11 exists to record:

```yaml
# The frames are already subsampled at every 30th video frame,
# so detection.frame_step is 1 here (1 over these images == 30 over the source
# video, which is what the release run used).
```

**Three things the analog does not answer, and the plan must decide:**

1. **Path absoluteness.** `config_paper.yaml` uses paths relative to the archive root, because
   `aquacal` is launched from there. The driver runs from the repo root and the image set is
   elsewhere on the Linux box, so this config needs absolute target paths (or the driver must
   `cd`). The pre-flight probe resolves them with a bare `pathlib.Path(p)` against the process
   cwd (`:956`), so a relative path resolves against the repo root — verify on the target.
2. **Where it lives.** Nothing under `experiments/*.yaml` is committed today; the only committed
   configs are `src/aquacal/config/example_config.yaml`, the three under `aquacal_data/real-rig/`,
   and `.planning/probes/2026-08-17-degeneracy-classification/config_paper_instrumented.yaml`.
   A new `experiments/configs/` directory is a clean choice — but check
   `emit_seed_variant_configs` / `emit_invocation_configs`' release-tree write refusal
   (`run_experiment_suite.sh:369-372`) does not fire against it.
3. **The `internals` block.** `E2_RELEASE_CONFIG` is the *source* the three invocation configs are
   generated from (`:376-386`), which differ only in `internals` keys. Confirm the committed
   config carries whatever base `internals` the generator expects — including Phase 25's
   `log_all_observation_depths`, which `all_observation_depths.csv`'s emission rides on.

---

### NEW — the emitter-coverage report (D-16) and the frozen-row note (D-19)

**Analog:** `experiments/EXPECTATIONS.md` (237 lines). This is the repo's established in-repo
verification note, and its conventions are worth copying wholesale:

- **A "why this exists, written before the fact" opener**:

```markdown
**Read this before judging a finished run.** It is written *before* the run, on purpose, because
the run is what it will be checked against -- a sheet assembled afterwards from what the run
happened to produce records the run, not the expectation.
```

- **A dense table with a per-row verdict and a per-row reason**, which is exactly D-16's
  27-artifact walk and D-19's frozen-row classification:

```markdown
| Script | `_run_check`? | `compare_experiment_csv` call sites | Schema state at the re-base |
|---|---|---|---|
| `e3_derived_quantities.py` | yes | 3 | Unmoved. **One of only two `--check` paths that is still a real reproduction signal** ... |
```

- **Anti-misreading callouts in bold**, stating what a green result does NOT prove. §4's heading
  is literally *"Existence and row count are not correctness"*. D-16's report needs the equivalent:
  *an emitter existing does not make the number right.*
- **Every claim carries a `file:line`** (`experiments/e4_benchmark_grid.py:215`,
  `experiments/check_rerun_gates.py:1378`). D-16's whole value is the `artifact -> emitter file:line`
  column; do not write it without one.

**For D-19 specifically**, `EXPECTATIONS.md` §2's "pre-declared mismatch is expected output, not
a finding" framing is the exact tone required — the note converts "stale reference" into "stated
provenance", so each row needs **artifact, sha, machine, why-not-regenerated**. Three rows cite
`archive/e6-2026-08-02-...` / `archive/e2-2026-07-30-...`; six cite `results_linux32gb/...`; and
`RL-determinism` is unregenerable because P26-D-42 turned `e6_repeat2` off — a fact the manifest
already pins negatively via `test_expectations.py::test_no_expectation_names_results_e6_repeat2`
(`:353`).

**Placement:** `experiments/` alongside `EXPECTATIONS.md` and `README.md` for D-16 (it is about
emitters, i.e. code); `.planning/` for D-19 is defensible since Phase 30 consumes it — but
`experiments/` keeps both discoverable from the driver's own directory. Author's discretion per
CONTEXT.

---

### `tests/unit/test_run_experiment_suite_dryrun.py` — driver tests for D-22 (and D-10/D-14)

**Analog:** `TestResume` at `:479-527`, which already writes a hand-crafted state file into the
sandbox and asserts on `SKIP stage` in stdout. D-22's test is the third member of this class:

```python
    def test_a_started_but_uncompleted_stage_is_rerun_from_scratch(
        self, bash_available, tmp_path
    ):
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        sha = _frozen_sha()
        state_file = state_dir / f"run_experiment_suite_state.{sha}.dryrun.tsv"
        state_file.write_text(
            "e5\t7\tstart\t2026-08-18T00:00:00.000Z\t\n", encoding="utf-8"
        )

        run = run_driver(tmp_path)
        assert run.returncode == 0
        assert "e5" in run.stage_invocations(), (...)
        assert "SKIP stage 7 (e5)" not in run.stdout, (...)
```

D-22's version writes a **complete line with a non-zero exit code** and asserts the stage is
re-invoked:

```
e5	7	start	2026-08-18T00:00:00.000Z	
e5	7	complete	2026-08-18T00:00:01.000Z	1
```

The harness (`run_driver`, `:245-329`) is fully sandboxed and is the only sanctioned way to
invoke the driver from a test — it sets the seam, redirects `SUITE_OUT_DIR` / `SUITE_STATE_DIR`,
and always passes an explicit `timeout=`:

```python
    env["RUN_EXPERIMENT_SUITE_DRY_RUN"] = "1"
    env["RUN_EXPERIMENT_SUITE_DRY_RUN_CMD"] = stub
    env["SUITE_OUT_DIR"] = out_dir.as_posix()
    env["SUITE_STATE_DIR"] = state_dir.as_posix()
    ...
    completed = subprocess.run(
        [_resolve_bash(), DRIVER_PATH.as_posix(), *args],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=timeout,
    )
```

For **D-14**, the analog is `TestConcurrencyConstraints` (`:619-770`), whose tests read
`STAGE_CONCURRENCY` semantics out of the manifest fixture and assert against parsed state events
(`test_no_serial_alone_stage_ever_shares_the_box`, `:711`). A thread-pin test asserts on the
dispatch log (`SUITE_DISPATCH_LOG`) or a stub that echoes `OMP_NUM_THREADS` — the `stub=`
parameter of `run_driver` exists for exactly this.

For **D-10**, `TestPreflight` (`:568-618`) already covers the refusal-names-its-flag rule and the
`--skip-e2` declared-reduction path; a directory-based frameset fixture slots in there.

---

## Shared Patterns

### 1. Expected values live in `suite_expectations.json`, never in a shell or Python literal

**Source:** `experiments/run_experiment_suite.sh:913-940`, and the manifest's own prose.
**Apply to:** D-10, D-14, D-20, D-24.

```python
manifest = json.loads(
    pathlib.Path("experiments/suite_expectations.json").read_text(encoding="utf-8")
)
frameset = manifest["preflight"]["frameset"]
cheap = frameset["cheap_check"]
```

The manifest states the rule about itself:

```json
"description": "E2's frameset IDENTITY signature (D-17). Pre-flight asserts IDENTITY, not mere presence, and the driver reads these numbers FROM HERE -- never from a literal in the shell script, which is how the retired archive's numbers survived in a code comment (FIX-06)."
```

The one sanctioned exception is documented at the exception site, with the reason
(`check_rerun_gates.py:984`): `# NOT derived from the manifest and NOT changed: the 'cameras'
axis survives D-40.` If a plan adds a constant, it must carry that kind of comment.

### 2. Every number in the manifest carries its own rationale field

**Source:** `experiments/suite_expectations.json` — `rows_rationale`, `n_extrinsic_videos_rationale`,
`min_total_bytes_rationale`, `free_space_floor_rationale`, `refusals_cut`, `declared_reduction_rationale`.
**Apply to:** D-10 (if the byte floor is re-derived from a target measurement), D-20 (each retag).

```json
  "min_total_bytes": 4000000000,
  "min_total_bytes_rationale": "A crude discriminator, not an estimate. The current frameset is 4.35 GB as published and 10.57 GB as the local raw capture; the retired ~4.3x-subsampled extraction is far below this floor. Its ONLY job is to separate the two archives."
```

A changed number without a changed rationale is the FIX-06 shape again.

### 3. Pre-flight is the only place permitted to abort, and every refusal names its flag

**Source:** `run_experiment_suite.sh:1848-1858` (the D-50 restatement) and
`suite_expectations.json:preflight.overrides` (five entries).
**Apply to:** D-10, D-12, D-13.

```bash
        log "FATAL: OVERRIDE FLAGS, one per refusal -- --skip-e2 (frameset absent, DECLARES a synthetic-only run), --allow-frameset-mismatch (frameset identity), --allow-nonempty-out (...), --allow-low-disk (...), --allow-gate-precheck-failure (...). Run with --help for the full list."
```

Corollary: **no new refusal and no sixth override in Phase 27.** § D cut three; D-12 says do not
add a fourth.

### 4. Gates record; only pre-flight aborts, and the verdict travels in a FILE

**Source:** `run_experiment_suite.sh:707-712`, `:720-747`.
**Apply to:** D-20, and anything touching `run_gate_check`'s caller.

```bash
record_failure() {
  # D-01. Append one finding to the sticky failure log. Called from the parent
  # AND from concurrent child processes, which is why it appends to a file:
  # a child cannot set `SUITE_FAILED` in its parent. ...
  printf '%s\n' "$*" >>"${SUITE_FAILURE_LOG}"
}
```

`run_gate_check` **always returns 0**; the caller reads `LAST_GATE_EXIT`. Do not change that.

### 5. Provenance helpers never raise; a missing source is `None`, and a gate turns `None` into a FAIL

**Source:** `experiments/_run_manifest.py:113-135`, `:207-211`.
**Apply to:** D-13's lockfile emitter, D-14's manifest fields.

```python
    try:
        completed = subprocess.run(["git", *args], cwd=_REPO_ROOT,
                                   capture_output=True, text=True, check=False)
    except (OSError, ValueError):
        logger.debug("git %s could not be executed", " ".join(args))
        return None
    if completed.returncode != 0:
        logger.debug("git %s exited %d", " ".join(args), completed.returncode)
        return None
    return completed.stdout.strip()
```

### 6. A manifest edit is a three-file change

**Source:** `experiments/EXPECTATIONS.md` header + `render_expectation_sheet.py`.
**Apply to:** D-20, D-10-if-the-floor-moves, D-24-if-a-finding-requires-an-edit.

`suite_expectations.json` -> `python -m experiments.render_expectation_sheet --write` ->
`tests/unit/test_expectations.py`. Skipping the middle step leaves the suite red.

### 7. Non-`v*` tags already exist in this repo and the tooling knows it

**Source:** `experiments/_run_manifest.py:104-108`.
**Apply to:** D-01/D-02/D-03.

```python
#: `git describe` is restricted to VERSION tags. This repository also carries
#: non-version tags -- `pre-rerun-baseline` is created by this very phase -- and
#: an unrestricted `--tags` would anchor the manifest to whichever tag happened
#: to be nearest, silently replacing the semantic version anchor D-18 asks for.
_VERSION_TAG_GLOB = "v[0-9]*"
```

So `rerun-freeze-NN` is safe for the manifest's `git_describe` **and** for CI (`publish.yml`
triggers on `v*` only) — but note the driver's own `FROZEN_SHA` / sha-derived state path read
`git rev-parse`, not `describe`, so the state-file name will follow the sha, not the tag.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| The on-target verification loop (D-05/D-06/D-07: SSH clone, env build, dry run, `fd_jacobian`, gate roll-up) | process | remote execution | Nothing in this repo drives a remote host. There is no `ssh`/`scp` anywhere in `experiments/` or `src/`. Every step must be an individually-timeboxed plan step under the 600 s ceiling (CLAUDE.md); the planner should model it on the **structure** of `TestPreflight`/dry-run invocation, not on any existing remote-execution code, because none exists. |
| A thread-pinning precedent | env config | — | Confirmed by CONTEXT § D-14: **no thread limit is set anywhere in `src/` or `experiments/` today.** D-14 introduces the first one. Use the `STAGE_CONCURRENCY` consumption pattern (`:2008`, `:2040`) for the *decision*, and invent only the export itself. |
| An in-repo `pip freeze` / lockfile artifact | provenance | subprocess -> text | No lockfile exists. `requirements.txt` and `pyproject.toml` are the shipped package's contract and D-13 explicitly does not touch them. Template from `_run_manifest.py`'s module shape instead. |

---

## Metadata

**Analog search scope:** `experiments/`, `src/aquacal/io/`, `src/aquacal/config/`, `tests/unit/`,
`aquacal_data/real-rig/`, `.planning/probes/`, `.github/workflows/`
**Files read:** `run_experiment_suite.sh` (4 non-overlapping ranges), `check_rerun_gates.py`
(5 ranges), `_expectations.py` (full), `_run_manifest.py` (3 ranges), `reconstruction_bootstrap.py`
(3 ranges), `e4_benchmark_grid.py`, `e5_index_sensitivity.py`, `test_run_experiment_suite_dryrun.py`
(2 ranges), `suite_expectations.json` (programmatic), `EXPECTATIONS.md`, `config_paper.yaml`,
`example_config.yaml`
**Pattern extraction date:** 2026-08-19
