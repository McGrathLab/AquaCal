# Phase 25: Degeneracy Classification & Claim Licensing - Pattern Map

**Mapped:** 2026-08-18
**Files analyzed:** 22 (8 library · 4 experiments · 4 probe/doc artifacts · 6 test files)
**Analogs found:** 21 / 22 (one file — the probe classification table — has a partial analog only)

> **Key framing (from RESEARCH § Don't Hand-Roll):** *"every mechanism this phase needs already
> exists in this repo… The phase's real work is placement, not construction. Any new helper is a
> signal that an existing one was missed."* This map therefore names, for every touched file, the
> **exact sibling already in that file** to copy — not a distant module.

---

## File Classification

### Library (`src/aquacal/`)

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/aquacal/calibration/_optim_common.py` (MOD) | optimization core / residual | batch transform + opt-in out-param sink | **itself**: `degeneracy_breakdown_out` block at `:764, :797-802, :823-849, :858-864` | exact (in-file sibling) |
| `src/aquacal/calibration/interface_estimation.py` (MOD) | solver call site | request-response (post-solve single eval) | **itself**: `:609-622` + `:365-378` stage resolution | exact (in-file sibling) |
| `src/aquacal/calibration/refinement.py` (MOD) | solver call site | request-response | `interface_estimation.py:609-622` — the two are **line-for-line identical in shape** | exact |
| `src/aquacal/calibration/_observability.py` (MOD) | vocabulary / comment-block commentary | none (declarative) | **itself**: the two `# ---` comment blocks at `:36-59` and `:62-84` | exact |
| `src/aquacal/config/schema.py` (MOD) | config dataclass | declarative | `save_conditioning` / `benchmark_memory` at `:363-364` + docstring `:301-315` | exact |
| `src/aquacal/calibration/pipeline.py` (MOD) | orchestration / config parse + thread | request-response | `save_conditioning`: `:388 → :423 → :1038/:1043` | exact |
| `src/aquacal/validation/diagnostics.py` (MOD) | report writer | file-I/O (CSV sidecar) | **itself**: `depth_errors.csv` write at `:952-954`, `discard_stats` param at `:853`/`:944-945` | exact |
| `src/aquacal/cli.py` (MOD, optional) | config template | file-I/O | `:626-629` commented `internals:` template lines | exact |

### Experiments (`experiments/`)

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `experiments/_degeneracy.py` (MOD) | classifier + sidecar writer | transform + file-I/O | **itself**: `summarize_degeneracy_columns` (classifier shape) + `write_degeneracy_breakdown` (writer shape) | exact |
| `experiments/e1_refractive_comparison.py` (MOD) | experiment harness | batch / seed-band loop | **itself**: `_run_band` `:958-1075`, `_runner` `:1010-1046`; cross-script: `e7_interface_ablation._run_band` | exact |
| `experiments/e4_benchmark_grid.py` (MOD) | experiment harness / LaTeX emitter | file-I/O + guard | **itself**: `GRID_COLUMNS` comment at `:524-530`, `blocks` list at `:1587-1597`, guard at `:947-961` | exact |
| `experiments/e6_generalization_sweep.py` (MOD) | experiment harness / guard | event-driven gate | **itself**: three-branch gate at `:1098-1124` (already carries D-19.3-11 comments) | exact |

### Probe & documentation artifacts

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/probes/2026-08-17-degeneracy-classification/FINDINGS.md` (NEW) | probe record | doc | `.planning/probes/2026-08-17-huber-knee/FINDINGS.md`, `2026-08-17-optimality-decomposition/FINDINGS.md` | exact |
| `<probe>/degeneracy_classification.csv` (NEW) | provisional data table | file-I/O | `e7_focal_standoff.csv::scope` free-text column (FIX-04) — see § No Analog Found | partial |
| `<probe>/config_paper_instrumented.yaml` (NEW) | config copy | config | `aquacal_data/real-rig/real-rig/config_paper.yaml` + `cli.py:626-629` internals block | role-match |
| `.planning/MANUSCRIPT-FINDINGS.md` (MOD, MF-21) | doc | doc | MF-20 at `:2047` (last entry) | exact |

### Tests (Wave 0 — all six files already exist; **extend, never create**)

| Test File | Existing size | What it already contains | New tests |
|-----------|---------------|--------------------------|-----------|
| `tests/unit/test_optim_common.py` | 1326 lines | `TestDegeneracyBreakdownOut` (`:1138-1258`), `TestInvalidProjectionKeepsGradient._packed()` (`:918-1008`) — the scene generator that lifts frame 1 above water | 4 (detail sink, inert, index_spaces, recomputed_geometry) |
| `tests/unit/test_discard_accounting.py` | 912 lines | `test_clean_run_emits_degeneracy_keys_at_zero` (`:627`), `test_absent_stage_lands_in_the_unattributed_bucket` (`:667`), `test_reason_array_is_none_during_the_solve` (`:717`, the spy pattern), `_breakdown()` factory (`:781`) | 3 (stage_stamped, row_cap, classify) |
| `tests/unit/test_diagnostics.py` | 1475 lines | `TestSaveDiagnosticReport` (`:579-845`) with six `save_diagnostic_report(...)` invocations over `tempfile.TemporaryDirectory()` | 2 (sidecar absent / present) |
| `tests/unit/test_e1_band_mode.py` | 248 lines | `TestCli`, `TestMergeBandColumns` (pure), `TestBandMode` (**8 real-solve smoke tests**, PITFALL B2 blast radius), `TestSingleSeedPathUnaffected` | 3 (noise_axis_shape, no_duplicate_keys, smoke-unchanged) |
| `tests/unit/test_experiments_e4.py` | 1611 lines | `test_latex_fragment_separates_real_rig` (`:711-732`) — reads the written `.tex` and asserts on its text | 1 (optimality_caveat) |
| `tests/unit/test_experiment_inertness.py` | 195 lines | AST-based `_count_references`, module-path constants `_E1_PATH`…`_E7_PATH`, `read_text()` substring assertion at `:132-133` | 2 (stated_domain, gate_rationale) |

---

## Pattern Assignments

### `src/aquacal/calibration/_optim_common.py` — the detail sink (DEGEN-04, D-06/D-06b/D-10)

**Analog: the file's own `degeneracy_breakdown_out` implementation.** Copy all four of its parts.

**1 — Signature (`:670-686`), the slot the new param goes in:**

```python
def compute_residuals(
    params: NDArray[np.float64],
    ...
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
    shared_interface: bool = True,
    invalid_count_out: list[int] | None = None,
    degeneracy_breakdown_out: dict[str, int] | None = None,
) -> NDArray[np.float64]:
```

> `compute_residuals` has **no** `discard_stage` parameter and must not gain one (D-07 is satisfied
> at the caller). Verified against the full signature.

**2 — Opt-in allocation discipline (`:764`, `:797-802`) — copy the comment voice, not just the code:**

```python
record_degeneracy = degeneracy_breakdown_out is not None
...
    # D-06b: the reason array is allocated ONLY when a breakdown was
    # requested, and a breakdown is requested only on the single post-solve
    # evaluation. The solve's own thousands of residual calls therefore
    # allocate nothing and pay one identity test.
    nan_reason = (
        np.zeros(len(points_3d), dtype=np.int8) if record_degeneracy else None
    )
    projected_batch = refractive_project_batch(
        camera, interface, points_3d, nan_reason_out=nan_reason
    )
```

**3 — The fill block (`:823-849`), inside `if invalid.any():` — the exact enclosing scope.** Loop
variables live here: `frame_idx`, `cam_name`, `detection`, `camera`, `points_3d`, `nan_reason`,
`invalid`, `unextendable`, `water_zs[cam_name]`. Note the **two index spaces** the existing block
already navigates — this is the highest-risk part of the diff:

```python
                if record_degeneracy:
                    # Two independent axes. There is no tie-break rule ordering one
                    # cause ahead of another, and none may ever be introduced -- the
                    # reason array already assigns exactly one cause per point.
                    ...
                    invalid_reasons = nan_reason[invalid]      # index space i (full point set)
                    ...
                    n_this_penalized = int(unextendable.sum()) # index space k (over points_3d[invalid])
```

`unextendable` is built at `:825` from `_extend_invalid_projections(camera, points_3d[invalid])`, so
it is indexed by `k`; `nan_reason` and `detection.corner_ids` are indexed by `i`. RESEARCH names
mixing them **"the most likely bug in this diff"**.

**4 — The out-parameter fill (`:858-864`) and its "assigned, not accumulated" contract:**

```python
    if degeneracy_breakdown_out is not None:
        degeneracy_breakdown_out["above_interface"] = n_above_interface
        ...
        degeneracy_breakdown_out["observations_evaluated"] = n_observations_evaluated
```

**5 — Docstring pattern for the new param (`:717-747`).** `degeneracy_breakdown_out`'s Args entry is
~30 lines: it states the inert default, what is filled, the closed key set, the caller-owns-the-names
rule, and a domain caveat about what the quantity does *not* mean. Match that register — the new
sink's entry must state `h_q`/`h_c`/`r_q` are **meters**, that `nan_reason` stays an **int8 code**
(never a name), and that `stage` is added by the caller.

**6 — Module-level constant precedent for the D-10 row cap (`:31-35`):**

```python
#: Residual (pixels) assigned to an observation whose projection cannot be
#: extended at all -- the point lies behind the camera, so not even the pinhole
#: limit is defined. This is the historical flat penalty, now confined to the
#: one case where no continuous extension exists.
INVALID_PROJECTION_PENALTY_PX = 100.0
```

Same `#:` Sphinx-comment form for `ROW_CAP_PER_STAGE = 50_000`.

**Geometry recompute — the source expressions to match bit-for-bit** (`core/refractive_geometry.py:661-679`):

```python
    C = camera.C
    z_int = interface.get_water_z(camera.name)
    h_c = z_int - C[2]                         # :661-662
    ...
    h_q = Q[:, 2] - z_int  # (N,)              # :675
    dx = Q[:, 0] - C[0]                        # :676
    dy = Q[:, 1] - C[1]                        # :677
    r_q = np.sqrt(dx * dx + dy * dy)  # (N,)   # :679
    valid = (h_q > 0) & (r_q >= 1e-10)         # :682
```

`r_p` (and therefore any true exit angle) exists **only** for points inside `valid` — the Newton loop
at `:713-741` never runs for a flagged point. Use the chord surrogate, named `chord_incidence_deg`.

---

### `src/aquacal/calibration/interface_estimation.py` and `refinement.py` — the two post-solve sites

**Analog: each other.** The two blocks are identical in shape; whatever lands in one lands verbatim
in the other. Do not diverge them.

**Stage resolution, already in scope** (`interface_estimation.py:365-378`; `refinement.py:199-210` is
the same block with the cross-reference comment flipped):

```python
    # Validate the discard stage label ONCE, at entry, before the solve (D-03).
    # An unrecognized string is a programming error; raising it after a
    # multi-minute solve would waste the solve. `None` maps to the declared
    # "unattributed" bucket. See the matching block in refinement.py.
    resolved_discard_stage = (
        discard_stage if discard_stage is not None else ("unattributed")
    )
    if resolved_discard_stage not in DISCARD_STAGES:
        raise ValueError(
            f"unrecognized discard_stage {discard_stage!r}; legal stages are "
            f"{list(DISCARD_STAGES)} (or None for {'unattributed'!r})"
        )
```

⇒ **D-07 is free.** The stamped stage inherits the closed-vocabulary guarantee.

**The call site to extend** (`interface_estimation.py:609-622`; `refinement.py:420-434` identical):

```python
    # D-06b: this `compute_residuals` call already runs AFTER `least_squares`
    # returns, and every diagnostic out-parameter is threaded here and ONLY here.
    # Nothing below is added to `cost_args` and nothing is threaded into the
    # callable scipy invokes -- doing so would allocate a reason array on every
    # one of thousands of residual evaluations, and nothing in the type
    # signatures would catch the drift.
    invalid_counts: list[int] = []
    degeneracy_breakdown: dict[str, int] = {}
    compute_residuals(
        result.x,
        *cost_args,
        invalid_count_out=invalid_counts,
        degeneracy_breakdown_out=degeneracy_breakdown,
    )
```

**Signature slot for the new sibling parameter** — `optimize_interface` (`:275-296`) ends:

```python
    diagnostics_out: SolverDiagnostics | None = None,
    discard_stats_out: dict[str, int] | None = None,
    water_z_bounds: tuple[float, float] | None = None,
    discard_stage: str | None = None,
) -> tuple[...]:
```

`joint_refinement` (`refinement.py:95-110`) ends with the identical four lines. Add
`degeneracy_details_out: list[dict] | None = None` in both.

**Aggregate-count independence (D-10) is already established here** — the count never comes from row
length:

```python
    n_invalid = invalid_counts[0] if invalid_counts else 0
    ...
    _bump(discard_stats_out, "degenerate_observations_at_solution", n_invalid)
```

---

### `src/aquacal/calibration/_observability.py` — the D-04 gate-scope rationale

**Analog: the file's own two banner comment blocks.** Copy the exact banner form and the
"here is the failure this prevents" voice:

```python
# ---------------------------------------------------------------------------
# Degeneracy split vocabularies (phase 24, DEGEN-02)
# ---------------------------------------------------------------------------
#
# TWO INDEPENDENT AXES, NOT A CROSS PRODUCT. ...
#
# Why not the 3x2 joint: it would be 18 kind keys plus 3 denominators, tripling
# the vocabulary to answer a question nobody has asked. The per-observation joint
# is explicitly DEGEN-04's (Phase 25); this phase reports the split and does not
# interpret it.
```

Note that block **already forward-declares this phase** — the new authored-vs-given block belongs
immediately after it, near `_DEGENERACY_CAUSES` (`:86-91`).

**Closed-vocabulary + raising-accessor pattern** if any new vocabulary is added (`:179-207`):

```python
def degeneracy_cause_key(cause: str, stage: str) -> str:
    ...
    if cause not in _DEGENERACY_CAUSES:
        raise ValueError(
            f"unrecognized degeneracy cause {cause!r}; legal causes are "
            f"{list(_DEGENERACY_CAUSES)}"
        )
```

**⚠ D-06 boundary:** the library spells no bucket name. The classifier's vocabulary belongs in
`experiments/_degeneracy.py`, **not** here. Only prose is added to this file.

---

### `src/aquacal/config/schema.py` + `pipeline.py` — the D-09 config flag path

**Analog: `save_conditioning` (and its twin `benchmark_memory`), end to end. Four sites, all verified.**

**1 — Field (`schema.py:363-364`), the exact slot:**

```python
    save_conditioning: bool = False  # Opt-in: Jacobian singular-value spectrum + parameter correlation matrix at the solution
    save_benchmark: bool = True  # Write output_dir/benchmark.json every run (BENCH-04); cheap, on by default
    benchmark_memory: bool = False  # Opt-in: per-stage-boundary peak-RSS reading in benchmark.json (BENCH-02)
```

**2 — Docstring `Attributes:` entry (`schema.py:301-305`):**

```
        save_conditioning: Opt-in. If True, computes and saves the Jacobian's
            singular-value spectrum and the full parameter correlation matrix at
            the solution under output_dir/internals/. Expensive (SVD + dense
            correlation matrix over hundreds of parameters) — off by default.
```

**3 — YAML parse (`pipeline.py:385-390`):**

```python
    # Observability hooks (see output_dir/internals/)
    internals = data.get("internals", {})
    save_stage_calibrations = bool(internals.get("save_stage_calibrations", True))
    save_optimization_trace = bool(internals.get("save_optimization_trace", False))
    save_conditioning = bool(internals.get("save_conditioning", False))
    save_benchmark = bool(internals.get("save_benchmark", True))
    benchmark_memory = bool(internals.get("benchmark_memory", False))
```

**4 — Constructor (`pipeline.py:421-425`):** `save_conditioning=save_conditioning,` beside
`benchmark_memory=benchmark_memory,`.

**5 — Consumer thread (`pipeline.py:1012-1033`):** the `_run_stage3` closure passes config fields
through by keyword; add the sink here, and at the `:1265-1283` intrinsic-pass call:

```python
    def _run_stage3(dets, observer=None, diagnostics_out=None):
        """Run Stage 3 interface optimization on the given detection set."""
        return optimize_interface(
            ...
            discard_stats_out=discard_stats,
            discard_stage="stage3_interface_optimization",
        )
```

**Note (from RESEARCH):** the `:1033` closure is invoked **twice** when `reject_outlier_frames` fires
(re-run at ~`:1187`) — the detail sink inherits the same cross-stage double-count property the Phase
24 counters have. That is expected, not a bug.

**Complete `discard_stage=` inventory — five sites, do not miss one:** `pipeline.py:156`,
`pipeline.py:1033`, `pipeline.py:1283`, `datasets/pipelines.py:171`, `datasets/pipelines.py:206`.

**6 — CLI template (`cli.py:626-629`), if the flag is surfaced to `aquacal init`:**

```python
            "internals:",
            ...
            "  # save_conditioning: false        # Jacobian spectrum + parameter correlation at the solution (expensive)",
```

---

### `src/aquacal/validation/diagnostics.py` — the D-08 sidecar (Option A)

**Analog: `discard_stats` (the last parameter added) and `depth_errors.csv` (the existing CSV write).**

**Signature (`:844-854`) — append the new param last, exactly as `discard_stats` was:**

```python
def save_diagnostic_report(
    report: DiagnosticReport,
    calibration: CalibrationResult,
    detections: DetectionResult,
    output_dir: Path,
    save_images: bool = True,
    auxiliary_reprojection: ReprojectionErrors | None = None,
    timings: dict[str, object] | None = None,
    frame_rejection: dict[str, object] | None = None,
    discard_stats: dict[str, int] | None = None,
) -> dict[str, Path]:
```

**Docstring pattern (`:876-880`) — the "why this exists" clause is part of the pattern:**

```
        discard_stats: Optional discard-counter totals (plan 19.2-26). Stored
            under the top-level ``"discard_stats"`` key in ``diagnostics.json``.
            This is how the degenerate-PnP guard's rejection count becomes
            auditable after a run -- the guard is otherwise silent.
```

**The CSV write (`:951-954`) — the precedent that makes a CSV in this module legitimate:**

```python
    # Save CSV
    csv_path = output_dir / "depth_errors.csv"
    report.depth_errors.to_csv(csv_path, index=False)
    result["csv"] = csv_path
```

**The conditional-key precedent for "written only when non-empty" (`:938-945`):**

```python
    # Add automatic frame-rejection summary if provided
    if frame_rejection is not None:
        json_data["frame_rejection"] = frame_rejection
    if discard_stats is not None:
        json_data["discard_stats"] = discard_stats
```

D-08 needs the stricter `if not degeneracy_details: return` (empty list ⇒ **no file at all**, not an
empty file). Also register the new path in the returned `dict[str, Path]` and in the docstring's
`Returns:` list (`:884-890`) and the `Creates:` list (`:858-863`).

**Call site (`pipeline.py:1616-1626`):**

```python
    save_diagnostic_report(
        diagnostic_report,
        temp_result,  # Full result for plots
        val_detections,
        config.output_dir,
        save_images=True,
        auxiliary_reprojection=aux_reproj,
        timings=timings_payload,
        frame_rejection=frame_rejection_info,
        discard_stats=dict(discard_stats),
    )
```

---

### `experiments/_degeneracy.py` — the classifier and its table writer (D-06)

**Analog: this 150-line module in its entirety.** Three patterns to copy:

**1 — Module-level closed vocabularies with the "why the name carries the axis" comment (`:35-53`):**

```python
#: The three causes and two fates, in the order their columns appear.
DEGENERACY_CAUSES = ("above_interface", "behind_camera", "interface_below_camera")
DEGENERACY_FATES = ("extended", "penalized")

#: The six append-only CSV columns, in the order every experiment appends them.
#: The `cause_`/`fate_` segment is a double-count mitigation, not decoration --
#: it is what stops a reader summing across the two axes -- and matches the
#: library's own `DISCARD_KEYS` spelling exactly...
DEGENERACY_COLUMNS: tuple[str, ...] = (...)
```

**2 — The classifier function shape (`summarize_degeneracy_columns`, `:70-112`).** Note the pattern of
a **discriminator guard before any `.get(..., 0)`** — the exact trap the new classifier must avoid
when mapping `nan_reason` codes:

```python
    # A NON-EMPTY dict from before this phase ... would otherwise floor to
    # 0 on every column via `.get(..., 0)`, reading as "measured and found
    # clean" for precisely the artifact class this convention protects. Absence
    # of the merged key is the discriminator...
    if not discard_stats or MERGED_DEGENERACY_COLUMN not in discard_stats:
        return {column: None for column in DEGENERACY_COLUMNS}
```

**3 — The writer shape (`write_degeneracy_breakdown`, `:114-150`), five steps, copy verbatim:**

```python
    path = Path(path)
    if path.exists() and not force:
        logger.warning(
            "Refusing to overwrite existing degeneracy breakdown sidecar %s "
            "-- re-run with --force to replace it.",
            path,
        )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(breakdown, f, indent=2, sort_keys=True)
    logger.info("Wrote degeneracy breakdown sidecar to %s", path)
```

**Bucket ↔ code mapping the classifier implements** (`refractive_geometry.py:30-33`, write sites
`:663-666`, `:690`, `:702`, `:757`):

| Constant | Value | Bucket |
|----------|-------|--------|
| `NAN_REASON_NONE` | 0 | never written (zero-init) |
| `NAN_REASON_INTERFACE_BELOW_CAMERA` | 1 | (c) `h_c <= 0` |
| `NAN_REASON_ABOVE_INTERFACE` | 2 | **(a)** `h_q <= 0` |
| `NAN_REASON_BEHIND_CAMERA` | 3 | **(b)** camera-model failure — the D-04 tripwire |

Bucket (b) is separated **by code, not by re-deriving a predicate on `h_q`** — the classifier's
verification criterion.

---

### `experiments/e1_refractive_comparison.py` — the `noise_std` axis (BAND-01)

**Analog: `_run_band` / `_runner` as they stand (`:958-1075`).**

**1 — The smoke collapse precedent, which is exactly how the noise list should collapse (`:992-993`):**

```python
    scenario_name = "ideal" if smoke else SCENARIO_NAME
    depths = [1.30] if smoke else None
```

⇒ `noise_levels = [None] if smoke else NOISE_LEVELS` (PITFALL B2: without this, all **8** existing
real-solve tests in `TestBandMode` quadruple).

**2 — The environment-once discipline (`:993-999`) — must stay outside the new loop too:**

```python
    # Captured ONCE before the seed loop -- capture_environment() shells out to
    # `git rev-parse` per call, and a per-cell call is what split an artifact's
    # recorded SHA before (CLAUDE.md / knowledge-base "Commit nothing during a
    # production run").
    environment = capture_environment()
```

**3 — The override site (`:1015`) — one line after `create_scenario`:**

```python
        scenario = create_scenario(scenario_name, seed=seed)
        results: dict = {}
```

The evaluation set follows for free via `_build_dataframes` (`:605`):

```python
        test_detections = generate_synthetic_detections(
            ...
            noise_std=scenario.noise_std,
            seed=depth_seed,
        )
```

> CONTEXT.md cites `:438` for this; the real line at `2a6aed2` is **`:605`**. The substance of D-11
> is unaffected.

**4 — The accumulator-out-of-closure pattern (`:1004-1009`, `:1032`) — the noise loop nests inside
`_runner`, and its stamp is applied to the inner block before returning:**

```python
    # `run_seed_band` returns ONE concatenated frame and stamps `seed` onto it
    # itself; it cannot return two, and its signature is shared with E7 so it
    # must not grow one. The parameter-level frames are therefore accumulated
    # here and stamped with `seed` inside the runner...
    exp1_frames: list[pd.DataFrame] = []
    ...
        exp1_frames.append(df_exp1.assign(seed=seed))
```

`.assign(noise_std=noise)` is the same idiom for the new axis. **Do not stamp `noise_std` in
`run_seed_band`** — that primitive is shared with E7 (`_io.py:166-217`) and its docstring pins its
contract to "call once per seed, stamp `seed`, concatenate".

**5 — The key-columns declaration (`:245-256`) — PITFALL B1, the highest risk in the phase:**

```python
# D-19.4-14: the band CSV carries every seed's rows, so `seed` joins the key
# columns -- (test_depth_m, model) alone is no longer unique once multiple
# seeds are concatenated (mirrors E7's BAND_KEY_COLUMNS convention).
BAND_KEY_COLUMNS = ["seed", "test_depth_m", "model"]
...
PARAMETER_BAND_KEY_COLUMNS = ["seed", "camera", "model"]
```

`write_experiment_csv` (`_io.py:241-292`) validates only that key columns **exist** — it does
`sort_values(by=key_columns, kind="stable")` and writes, with **no uniqueness check**. Both lists
must gain `noise_std`, or `compare_experiment_csv` (`_io.py:332-357`) meets duplicate keys.

**6 — The D-14 header site (`:56`), inside the module docstring, beside the demotion note:**

```
the "2 of 10 seeds exceed 2 mm" finding...  **E1
carries NO accuracy claim (D-19.3-17 demoted it)** -- this band exists for
reproducibility, not because E1's numbers move...
```

A second occurrence lives in the `scope` string at `:1104-1110`
(`"...neither asserts nor denies an accuracy claim for E1 (D-19.3-17 already demoted E1's own)."`) —
the sidecar-scope-sentence pattern, which RESEARCH recommends updating in the same pass so source
and artifact carry the same sentence.

---

### `experiments/e4_benchmark_grid.py` — the D-17 optimality caveat + D-04 rationale

**Analog A — the inline column comment (`:520-531`). This exact precedent already exists two lines
below the target column:**

```python
    "optimality_stage3_interface_optimization",
    "reprojection_rms",
    ...
    # D-19.3-11/plan 19.3-07: the final-solution guard count this cell's
    # calibrate_synthetic call recorded via discard_stats_out. Appended last
    # so every existing column keeps its position. Populated whenever a
    # cell's metrics are populated (status in {"ok", "degenerate",
    # "skipped_existing" with an on-disk record}); null when no
    # benchmark.json was ever read for this cell.
    "degenerate_observations_at_solution",
```

**Analog B — the `.tex` comment block (`:1587-1597`). The caveat is one more `%`-prefixed entry:**

```python
        blocks = [
            "% E4 compact summary (nine synthetic cells, main-text table)",
            summary_path.read_text(),
            "% E4 full grid (nine synthetic cells, supplement table)",
            full_path.read_text(),
            # See this function's docstring: the real-rig row is its own
            # block, never a tenth point on the nine-cell curve above (D-02).
            "% E4 real-rig anchor row (pipeline-written, end-to-end; see D-02)",
            real_rig_path.read_text(),
        ]
```

**Analog C — the guard block for the D-04 rationale (`:947-961`). The existing comment is the one to
extend; the predicate is untouchable (D-05):**

```python
        n_degenerate = discard_stats.get("degenerate_observations_at_solution", 0)
        if n_degenerate > 0:
            # D-19.3-11: recorded and warned about unconditionally, whether
            # this is a declared production cell or one of SMOKE_CELLS --
            # the GATE (ok -> degenerate) is applied downstream in
            # build_grid_dataframe, which only declared production cells
            # ever reach (SMOKE_CELLS never call it, see _run_smoke_cells),
            # so --smoke can never see a false failure from this count.
            logger.warning(...)
```

**Do NOT co-opt `status_reason`** — it is owned by the cell-status gate. **Do NOT add a `#` comment
line to the CSV** — it breaks `pd.read_csv` in `compare_experiment_csv` and E4's own `--check`.

---

### `experiments/e6_generalization_sweep.py` — D-04 rationale (+ optimality pointer)

**Analog: its own three-branch gate (`:1098-1124`)**, which already carries a D-19.3-11 comment on
each branch:

```python
        n_degenerate = discard_stats.get("degenerate_observations_at_solution", 0)
        if n_degenerate > 0 and is_smoke:
            # Smoke carve-out (D-19.3-11, plan 19.3-07): still recorded and
            # still warned about, but a --smoke configuration must never be
            # gated -- see the `is_smoke` parameter docstring above.
            ...
            outcome = {"status": "ok", "status_reason": "", "metrics": metrics}
        elif n_degenerate > 0:
            status_reason = (...)
            outcome = {"status": "degenerate", ...}
        else:
            outcome = {"status": "ok", "status_reason": "", "metrics": metrics}
```

RESEARCH flags scope-expansion: `optimality_stage3_interface_optimization` also ships in
`generalization_sweep.csv` / `generalization_sweep_band.csv` from this file. Minimum action is a code
comment in E6's column list pointing at the E4 caveat — **surface to the user, do not silently
expand**.

---

## Shared Patterns

### 1. Opt-in out-parameter, zero cost when `None`
**Source:** `_optim_common.py:764, :797-802`; `_observability.py:44-59`; `_observability.py:275-285`
(`_bump`).
**Apply to:** the detail sink, both solver signatures, the diagnostics sidecar param.

```python
def _bump(stats: dict[str, int] | None, key: str, n: int = 1) -> None:
    """Increment a discard counter, or do nothing when accounting is off.

    Args:
        stats: The caller's counter dict, or None to disable accounting. When None
            this is a single identity test -- the inert default path.
    """
    if stats is None:
        return
    stats[key] = stats.get(key, 0) + n
```

### 2. The library spells no vocabulary
**Source:** `_optim_common.py:751-752` (docstring) — *"The caller maps these six onto the flat
``DISCARD_KEYS`` names; this module deliberately holds none of those key strings."*
**Apply to:** the detail sink (emits int8 `nan_reason` codes), `experiments/_degeneracy.py` (owns
the bucket names).

### 3. Aggregate counts never derived from row length
**Source:** `interface_estimation.py:623` (`n_invalid = invalid_counts[0]`) + `:641`.
**Apply to:** D-10's row cap. The truncated table's true count comes from
`degeneracy_breakdown_out["..."]`, computed independently in the same pass. Unit test: cap at 3 with
10 flagged points; the breakdown still reports 10.

### 4. FIX-04 free-text column for provenance / truncation stamps (D-03, D-10)
**Source:** `e7_focal_standoff.csv::scope` — a same-value-per-row free-text sentence naming the
re-analysis, its source artifact, its bound, and the decision ID. No schema change, survives
`pd.read_csv`.
**Apply to:** the library sidecar and the probe classification table (git sha, `provisional`,
`truncated=true|false`, true count).
**Rejected alternatives (verified):** a leading `#` comment line (breaks every consumer); a separate
`*_provenance.json` (fails D-10's "a reader of the file alone" requirement).

### 5. Rich comment blocks carrying the falsification
Every instrumentation site in this codebase explains **the failure it prevents**, names the decision
ID, and states what must never be restored. Examples: `_optim_common.py:797-800`,
`_observability.py:44-59`, `refinement.py:456-467` (*"The old clause… must not be restored -- it was
measured false the same day it was written."*). New code in this phase must match this register.

### 6. Source-text assertion tests
**Source:** `tests/unit/test_experiment_inertness.py:132-133` (substring) and `:70-88` (AST
`_count_references`); `tests/unit/test_stale_provenance_strings.py:26-59` (repo-root anchoring +
`_read()` skip helper).
**Apply to:** the D-14 stated-domain test and the D-04 gate-rationale test.

```python
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]   # not cwd -- WR-06

def _read(path: pathlib.Path) -> str:
    if not path.is_file():
        pytest.skip(f"target file not found: {path}")
    return path.read_text(encoding="utf-8")
```

> ⚠ **Grep-hygiene trap, already burned once** (`test_experiment_inertness.py:57-68`): the original
> `_count_references` stripped `#`-comment lines and counted substrings, so a docstring asserting the
> invariant failed the gate that checked it. Any new source-text gate must be scoped by filename and
> must not be falsifiable by the prose asserting it.

### 7. Test scaffolding available for free

| Need | Reuse | Location |
|------|-------|----------|
| A scene with a known flagged population | `TestInvalidProjectionKeepsGradient._packed(lift_frame1_above_water)` → `(params, cost_args, cams, frame_order)` | `test_optim_common.py:918-1008`, already reused verbatim by `TestDegeneracyBreakdownOut._packed` at `:1145-1147` |
| Interface-below-camera case | `params[6 * (len(cams) - 1)] = -0.05` | `test_optim_common.py:1244-1248` |
| Proving a param is `None` on the hot path | the monkeypatched-projector **spy** | `test_discard_accounting.py:717-767` |
| A three-camera solve scene | `_build_three_camera_board_scene(seed=0, depth_range=(0.3, 0.5))` | `test_discard_accounting.py` (used at `:634`, `:667`, `:726`) |
| A breakdown dict without a solve | `_breakdown(*, above, behind, below, extended, penalized, evaluated)` | `test_discard_accounting.py:781-790` |
| Stubbing a solve inside a harness | `_patch_run_configuration_internals` — `monkeypatch.setattr(m, "calibrate_synthetic", ...)` filling `discard_stats_out` | `test_experiments_e6.py:1185-1209` — **the model for monkeypatching `_run_one_model`** |
| Asserting on a written `.tex` | `write_grid_latex(df, tex_path); text = tex_path.read_text()` + index-ordering assertions | `test_experiments_e4.py:711-732` |
| Config round-trip through YAML | build dict → `yaml.dump` → `load_config` → assert field | `test_pipeline.py:300-316`; defaults at `:160-171` |
| Sidecar-exists / sidecar-absent | `save_diagnostic_report(..., Path(tmpdir), save_images=False)` then assert on `result[...]` | `test_diagnostics.py:790-800` |

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `<probe>/degeneracy_classification.csv` header/metadata mechanism | data table | file-I/O | **RESEARCH verified: this repo has NO CSV header/metadata convention for provisional or truncation stamps.** `write_experiment_csv` (`_io.py:241-292`) emits a bare `df.to_csv(path, index=False)`; every committed CSV in `experiments/results/` starts with a bare header row. Use Shared Pattern 4 (the FIX-04 free-text column) — that is the nearest precedent, not an exact one. |
| An exit-angle column for flagged rows | — | — | `r_p` does not exist for any flagged point (Newton loop `refractive_geometry.py:713-741` runs only over `valid_indices`). No analog exists because the quantity has never been emitted. Use the chord surrogate `chord_incidence_deg = degrees(arctan2(r_q, h_c + h_q))`. |

**Gaps in the existing test surface the planner should not assume are covered:**

- VALIDATION.md marks *"the three fixed-contract CSVs' headers are byte-unchanged"* as `likely ✓`
  under `test_experiments_e1.py -k columns`. **Verified: no such test exists.** `test_experiments_e1.py`
  has 12 tests, none asserting `EXP1/EXP2/EXP3_COLUMNS`; the only column assertions live in
  `test_e1_band_mode.py:143,151,167` and are `>=` subset checks on the **band** CSVs.
- VALIDATION.md routes the D-09 config-flag test to `test_cli.py` + `test_internals.py`.
  **`test_internals.py` (57 lines) is about `io/internals.py` — `ensure_internals_dir` /
  `warn_if_overwriting` — not config flags.** The real `load_config` round-trip analog is
  `tests/unit/test_pipeline.py::test_load_config_with_internals_and_seed` (`:300-316`), with the
  defaults assertion at `:160-171`. `test_cli.py:697-704` covers only the `aquacal init` template
  text.

---

## Metadata

**Analog search scope:** `src/aquacal/{calibration,config,core,validation,io}/`, `experiments/`,
`tests/unit/`
**Files read:** 20 (11 source, 9 test) — all excerpts verified verbatim at `86b9fdb`
**Pattern extraction date:** 2026-08-18
**Read-only:** no source file was modified.
