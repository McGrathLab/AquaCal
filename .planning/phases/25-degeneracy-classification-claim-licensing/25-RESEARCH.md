# Phase 25: Degeneracy Classification & Claim Licensing - Research

**Researched:** 2026-08-17
**Repo HEAD at research time:** `2a6aed2`
**Domain:** in-repo instrumentation + experiment-harness extension (no external technology)
**Confidence:** HIGH (every finding below is read off this repo's source at `2a6aed2`; nothing is from training data)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Verbatim from `25-CONTEXT.md` § Implementation Decisions. **Do not re-litigate any of these.**

**DEGEN-04 — delivery boundary**

- **D-01:** Phase 25 runs **one local instrumented E2 now**, against the archive's `config_paper.yaml` under **OpenCV 4.13** (the pin matters — 198 at 4.13, 194 at 4.14), rather than waiting for Phase 28. Cost is a 48–87 min / ~10.26 GiB unattended run. Rationale: the answer is needed before the freeze so the gate-scope call and the disclosure sentence can both be settled against the 2026-08-21 deadline.
- **D-02:** The local run is **PROVISIONAL ONLY**. It settles the *mechanism* — which bucket dominates — and **no count from it reaches `MANUSCRIPT-FINDINGS.md`, the disclosure, or any §3-facing number**. Phase 29's frozen table is the sole source of every number. This preserves the single-source-of-truth premise the milestone exists to establish.
- **D-03:** The probe is isolated under `.planning/probes/2026-08-17-degeneracy-classification/` (the pattern `2026-08-17-optimality-decomposition/` already set), with `--out` pointed there so **nothing lands in `experiments/results/`**. The classification table carries an explicit provisional + git-sha stamp in its header. Both `FINDINGS.md` and the table are committed.
- **D-04:** Criterion 2 (the deferred degeneracy-gate scope decision) is settled **on mechanism, with a tripwire**. If bucket (a) `h_q <= 0` dominates, the gate stays **synthetic-only** and the authored-vs-given-geometry rationale is written into `_observability.py` **and both harnesses' guard blocks** (`e4_benchmark_grid.py`, `e6_generalization_sweep.py`) so a code reader meets the reasoning at the gate. A recorded trigger re-opens it: a materially populated bucket (b) in Phase 29's frozen table.
- **D-05:** Do **not** soften the synthetic gate into a threshold. `19.3-07-PLAN.md` is explicit: exactly `count > 0 -> degenerate`, smoke-path carve-out only.

**DEGEN-04 — artifact and flag surface**

- **D-06:** **Raw sink in the library, classifier in `experiments/`.** `compute_residuals` gains a detail sink alongside the existing `degeneracy_breakdown_out`, filled with **raw geometry only**: `(camera, frame_idx, corner_id, h_q, h_c, r_q, exit angle, extension-succeeded, stage)`. The bucketing and the CSV writer live in `experiments/_degeneracy.py`, beside `write_degeneracy_breakdown`. **The library never spells a bucket name.**
- **D-07:** `stage` is **mandatory**, not optional — the counter is a cross-stage sum, so a per-observation record without its stage cannot be reconciled against the total.
- **D-08:** Ordinary users get a **`degenerate_observations.csv` sidecar** beside `diagnostics.json` in the normal output dir, **written only when at least one flagged row exists**. A clean rig writes nothing.
- **D-09:** Full-population `h_q` logging (**E2 only**, ~74k rows/stage, ~10 MB) is a **config schema field** consumed by `run_calibration_from_config` and threaded to the residual call. **Default off.** E2 reaches it through `config_paper.yaml`. Phase 26's driver passes it for E2 and nothing else.
- **D-10:** Row cap of order **50k per stage**: truncate, keep the aggregate count **exact**, stamp `truncated: true` plus the true count **in the artifact's own header**, and warn.

**BAND-01 — noise axis**

- **D-11:** Thread the noise level by **overriding `scenario.noise_std` before the solve**. No `create_scenario` signature change.
- **D-12:** The axis is **band-only**. It lives inside `_run_band`; `_run_smoke`, `_run_check` and the single-seed run keep today's behaviour at the scenario default. Only `exp1_band.csv` gains the column.
- **D-13:** The two-factor movement gets an **anti-confusion note, not an emitter and not a computed delta**. Record that the 0.5 px row is the clean `normal_fixed` isolator.
- **D-14:** The **stated domain** is recorded in **two** places: `e1_refractive_comparison.py`'s header **beside the existing D-19.3-17 demotion note**, and an **MF-NN entry in `.planning/MANUSCRIPT-FINDINGS.md`**.

**DEGEN-05 — verdict and the optimality caveat**

- **D-15:** The convergence question is **already answered and must not be re-derived.** Warm restarts recover no cost (largest relative drop 1.8e-9), so E1's non-refractive baseline is converged, the comparison is fair, and the **97–178× band is strengthened, not caveated**.
- **D-16:** The caveat that travels with the band is the baseline arm's severe ill-conditioning (~3e8 directional curvature), worded as **a property of fitting a pinhole model to refracted data — expected, not a defect, and explicitly not a reason to qualify the accuracy claim**. Stated **paired with** the converged-baseline finding.
- **D-17:** **Label `optimality` now, FIX-04 style.** `optimality_stage3_interface_optimization` ships in `benchmark_grid.csv` and `benchmark_grid.tex` to Zenodo with no caveat. Attach the caveat where the number ships. Pre-freeze is the last moment this can land.
- **D-18:** The four committed Phase 23 documents carrying the falsified pin-mechanism get **supersession headers pointing at the probe FINDINGS.md, bodies untouched** — `23-VALIDATION.md:72-74`, `23-RESEARCH.md:76`, `23-01-PLAN.md:103`, `23-01-SUMMARY.md:153`.
- **D-19:** The **Huber knee objection is CLOSED by measurement.** Measured at `054d753`: −1.09% at the deepest test point (123.87× → 122.52×), at most 6.83% anywhere, against a ~±30% seed band. Untouched refractive arm reproduced bit-for-bit. **Consequence for planning: this is no longer a plan task** — what remains is **one recorded sentence in the DEGEN-05 verdict**. **Do not** change the library's `f_scale`.

### Claude's Discretion

- Exact column names and dtypes of the per-observation table, and the CSV header/metadata mechanism used to carry the provisional + truncation stamps.
- The config key's exact name and where it sits in `schema.py`.
- Plan decomposition and commit granularity (subject to D-20's one-commit-per-requirement habit established in Phases 23/24).
- Whether the classifier is a function or a small module inside `experiments/_degeneracy.py`.

### Deferred Ideas (OUT OF SCOPE)

- **The `f_scale` re-tuning itself.** Post-submission; nothing measured says the symmetric rule is better.
- **WR-02**, Phase 24's open reviewer warning (zero-denominator / all-zero-cause edge case). Tracked in `.planning/todos/pending/2026-08-17-close-open-phase-24-review-warnings.md`; not this phase.
- **The distinct-vs-summed count question.** Recoverable only from the frozen Phase 29 table, per D-02.
- Not in this phase: the frozen E2 run and its committed classification table (Phases 28/29), the driver/gate registration itself (Phase 26/27 consume this phase's outputs), and any manuscript prose. `Spinoffs/papers/aquacal/` is **read-only from this repo**.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **DEGEN-04** | The production rig's 198 unprojectable observations are classified, with the finding recorded so the manuscript can disclose the count and say what it is (`REQUIREMENTS.md:84`) | § Detail Sink — Exact Seam; § The Two Post-Solve Call Sites; § The Config Flag Path; § The Sidecar's Home; § Row Cap and Truncation Stamps; § E2 Run Mechanics |
| **BAND-01** | E1's seed band gains a `noise_std` axis, so its promoted absolute-accuracy numbers carry a stated domain; `n_cameras` explicitly skipped (`REQUIREMENTS.md:180`) | § E1 Band Harness — Exact Nesting; § The 640-Row Reconciliation; § **PITFALL B1 (key uniqueness)**; § The D-14 Header Site |
| **DEGEN-05** (verdict only) | The first-order optimality reported by each stage is decomposed by parameter block (`REQUIREMENTS.md:87`) — instrumentation was Phase 24's; this phase carries the verdict forward | § The `optimality` Labelling Target; § **D-18 is already done**; § DEGEN-05 Verdict Deliverables |

</phase_requirements>

---

## Summary

This phase touches no new technology. Every unknown the planner faces is a **seam** question inside
this repo, and this document closes them by reading the source at `2a6aed2`.

Three findings materially change the plan's shape versus what CONTEXT.md assumed:

1. **D-18 is already complete.** All four Phase 23 documents already carry `> **CORRECTED
   2026-08-17 (post-phase)...**` blockquote headers citing
   `.planning/probes/2026-08-17-optimality-decomposition/`, landed in commit **`02fe224`**
   ("docs(23): correct the falsified optimality mechanism in four phase artifacts"). D-18 collapses
   from an implementation task to a **one-command verification**.

2. **The BAND-01 noise axis breaks two CSV key contracts unless `noise_std` joins them.** With four
   noise levels, `BAND_KEY_COLUMNS = ["seed", "test_depth_m", "model"]` no longer identifies a row
   in `exp1_band.csv` (four rows per key), and `exp1_parameter_band.csv` — which `_run_band` also
   writes, keyed `["seed", "camera", "model"]` — silently quadruples to 960 rows with fully
   duplicated keys. `write_experiment_csv` does **not** validate uniqueness; it only sorts. This is
   the single highest-risk item in the phase. See **PITFALL B1**.

3. **The BAND-01 run is ~7 hours, not ~1.8.** The committed 10-seed band took **6319.67 s** of
   wall clock (`e1_seed_band_provenance.json:seconds`). Four noise levels ⇒ 40 cells ⇒ **≈ 7.0 h**.
   CONTEXT.md's "400 s of solver time" is *solver only* for a single seed and excludes detection
   generation, the eight-depth evaluation sweep, and reconstruction. Under CLAUDE.md this is an
   **orchestrator-only, `nohup` + `disown` run** — the same class as the E2 run, and it must not be
   dispatched to an executor.

Beyond those, the detail sink has one real design fork: `h_q`, `r_q` and `h_c` are computed **inside
`refractive_project_batch`**, not in `compute_residuals`' scope. They are trivially recomputable at
the `compute_residuals` call site from data already in hand (three lines, exact same arithmetic), so
no projector signature change is required. But the **exit angle is not recoverable at all** for a
flagged observation — Newton never runs for points excluded by the `valid` mask, so `r_p` does not
exist for them. D-06's column list needs a defined surrogate; § Detail Sink proposes one.

**Primary recommendation:** Plan five commits — (1) the library detail sink + config flag, (2) the
`experiments/_degeneracy.py` classifier + sidecar writer, (3) BAND-01's noise axis with `noise_std`
added to **both** band key lists, (4) DEGEN-05's optimality labelling + verdict record + D-18
verification, (5) the gate-scope rationale (D-04) written after the E2 run reports its dominant
bucket. Schedule both long runs (E2 ≈ 48–87 min; E1 band ≈ 7 h) as orchestrator-owned detached
jobs; every executor gets a targeted `pytest` command only.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-observation raw geometry capture | **Library** (`_optim_common.compute_residuals`) | — | It is the only place the flagged mask, the `unextendable` mask, and the identity of `(camera, frame_idx, corner_id)` co-exist |
| Stage attribution of a detail row | **Library call sites** (`interface_estimation.py`, `refinement.py`) | — | `compute_residuals` has no `discard_stage` parameter and must not gain one; both callers already hold `resolved_discard_stage` (verified) |
| Bucket naming / taxonomy | **`experiments/_degeneracy.py`** | — | Established pattern: the library holds no key strings (D-06, `_observability.py:60-120`) |
| Sidecar CSV write for ordinary users | **Library** (`pipeline.py` → `validation/diagnostics.py`) | — | D-08 puts it beside `diagnostics.json`, which no experiment script touches |
| Full-population `h_q` opt-in | **Config schema** (`CalibrationConfig`) → `load_config` → `pipeline.py` | Phase 26 driver | D-09: the flag's state must be captured in the run's own provenance |
| `noise_std` axis | **`experiments/e1_refractive_comparison.py::_run_band`** | `experiments/_io.py` (untouched) | D-12: band-only; `run_seed_band` signature is shared with E7 and must not grow |
| `optimality` caveat text | **`experiments/e4_benchmark_grid.py`** (`.tex` comment blocks + column comment) | `.planning/MANUSCRIPT-FINDINGS.md` | FIX-04 precedent: label where the number ships, no schema change |
| Gate-scope rationale prose | **`_observability.py` + E4/E6 guard blocks** | — | D-04: a code reader must meet the reasoning at the gate |

---

## Project Constraints (from CLAUDE.md)

Directives the planner must honor. These carry the same authority as locked decisions.

| Directive | Consequence for this plan |
|-----------|---------------------------|
| **Never let a subagent background a long run** | Both the instrumented E2 (48–87 min) and the E1 noise band (**≈ 7 h**, measured) are **orchestrator jobs**. State explicitly in each plan what an executor must NOT run. |
| **The full suite is the orchestrator's job** | Each executor gets a targeted `pytest tests/unit/test_<file>.py` command; the orchestrator runs unfiltered `pytest tests/` at the post-merge gate. `-m "not slow"` is ~26 min and does not help. |
| **Always `python -u`** for long calibration runs | The E2 invocation line must be `python -u`, detached with `nohup` + `disown`. |
| **Never trust a subagent's return text** | Verify against `git log --oneline <base>..<worktree-branch>` and `git -C <worktree> status --porcelain`. |
| **Worktree executors must `export PYTHONPATH="$(pwd)/src"`** | Otherwise pytest tests `main`'s code, not the worktree's (memory: worktree-editable-install-resolves-to-main). |
| Coordinate system: +Z down, interface normal `[0,0,-1]`, all internal units meters | The detail sink's `h_q`/`h_c`/`r_q` are meters; the classifier docstring must say so. |
| `interface_distance` is the **Z-coordinate of the water surface**, not a per-camera distance | `h_c = water_z - C_z` is the physical gap; already correct in the code. |
| Ruff formatter; Google docstrings; `NDArray` type hints with shapes | New functions follow this. |
| Tests: one unit test file per source module, `tests/unit/` | New tests go in the existing `test_discard_accounting.py` / `test_e1_band_mode.py` / `test_optim_common.py`. |

---

## The Detail Sink — Exact Seam

### `compute_residuals` as it stands

`src/aquacal/calibration/_optim_common.py:670-871`. Signature ends:

```
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
    shared_interface: bool = True,
    invalid_count_out: list[int] | None = None,
    degeneracy_breakdown_out: dict[str, int] | None = None,
) -> NDArray[np.float64]:
```

- `record_degeneracy = degeneracy_breakdown_out is not None` at **:764**.
- The `nan_reason` array is allocated per-(camera, frame) at **:797-799**, only when `record_degeneracy`.
- The `if record_degeneracy:` block runs at **:823-849**, inside `if invalid.any():`.
- The fill of the six output keys is at **:858-864**.
- The loop variables in scope inside the `if record_degeneracy:` block are: `frame_idx`, `cam_name`,
  `detection` (hence `detection.corner_ids`), `camera`, `interface`, `points_3d`, `nan_reason`,
  `invalid` (bool mask), `unextendable` (bool mask over `points_3d[invalid]`), `water_zs[cam_name]`.

**`compute_residuals` has NO `discard_stage` parameter.** Verified by reading the full signature.
Stage attribution therefore belongs to the caller (see next section), which is exactly what D-07
needs and costs nothing.

### `h_q`, `r_q`, `h_c` are NOT in scope — but are trivially recomputable

`src/aquacal/core/refractive_geometry.py`:

| Quantity | Line | Expression | Reachable in `compute_residuals`? |
|----------|------|-----------|-----------------------------------|
| `h_c` | `:661` | `z_int - C[2]` | **No** — but `water_zs[cam_name]` and `camera.C` are both in scope; recompute is one line |
| `h_q` | `:675` | `Q[:, 2] - z_int` | **No** — but `points_3d[:,2]` and `water_zs[cam_name]` are in scope |
| `r_q` | `:679` | `sqrt(dx² + dy²)` from `Q[:,0:2] - C[0:2]` | **No** — recompute from `points_3d` and `camera.C` |
| `r_p` (needed for exit angle) | `:723` (Newton), `:749` | only for points in the `valid` mask | **NEVER** — flagged points are excluded from `valid` by construction |

**Finding (HIGH confidence):** recomputing `h_q`, `h_c`, `r_q` at the `compute_residuals` call site
reproduces the projector's values **exactly** (same float64 arithmetic on the same inputs; `z_int =
interface.get_water_z(camera.name)` is `water_zs[cam_name]`, and `C = camera.C`). This avoids a
signature change to `refractive_project_batch`, which already carries three out-parameters and a
documented "nothing inside the Newton loop" invariant. **Recommend recompute, do not plumb.**

> A unit test should pin this: recomputed `h_q` must equal the projector's, bit-for-bit, on a
> hand-built case that exercises all three NaN branches.

### The exit angle is undefined for flagged rows — D-06's column needs a surrogate

`refractive_project_batch` computes `valid = (h_q > 0) & (r_q >= 1e-10)` at **:682**. A flagged
observation is, by definition, outside `valid` (or its `camera.project` returned `None`). The Newton
loop at **:713-741** runs only over `valid_indices`, so `r_p` — the interface crossing radius, and
the only input to an incidence/exit angle — **does not exist for any flagged point**.
`incidence_angle_deg` in the diagnostics dict at **:766** is likewise `valid`-only.

Three honest options for the planner, in order of preference:

1. **A chord incidence angle** `theta_chord = degrees(arctan2(r_q, h_c + h_q))` — the straight-line
   camera-to-corner angle from vertical. Always defined when `h_c + h_q != 0`; requires nothing new;
   and it is the *same quantity* the todo's preset table already reports ("max straight-line
   incidence", `2026-08-15-classify...md:130`), so it is directly comparable to the recorded
   `realistic` / `ideal` numbers. **Recommended.** Name the column `chord_incidence_deg`, not
   `exit_angle_deg`, so nobody mistakes it for the refracted angle.
2. Emit `NaN` in an `exit_angle_deg` column and document why. Honest but useless.
3. Extend the projector to fill an `r_p_out`. Rejected: it must write inside/after the Newton loop
   for points that never entered it, breaking the documented invariant at `:714-715`.

**Confidence: HIGH.** The `valid` mask, the loop bounds, and the diagnostics dict were read directly.

### Recommended sink shape

```python
degeneracy_details_out: list[dict] | None = None,   # opt-in, None => zero cost
```

A list of plain dicts, appended per flagged observation, filled only inside the existing
`if record_degeneracy:` block (guarded by a second `if degeneracy_details_out is not None:` so the
breakdown can still be requested without the details — E1/E5/E7 want exactly that). Fields, all raw:

| Field | Source in scope | dtype |
|-------|-----------------|-------|
| `camera` | `cam_name` | str |
| `frame_idx` | `frame_idx` | int |
| `corner_id` | `detection.corner_ids[invalid]` | int |
| `h_q_m` | recomputed | float |
| `h_c_m` | recomputed | float |
| `r_q_m` | recomputed | float |
| `chord_incidence_deg` | recomputed | float |
| `extended` | `~unextendable` | bool |
| `nan_reason` | `nan_reason[invalid]` (int8 code, **not** a name) | int |

`stage` is **added by the caller**, not here (D-07 satisfied at the call site — see next section).
`nan_reason` stays an int8 code in the library and is mapped to a name in `experiments/_degeneracy.py`,
holding the D-06 line that the library spells no vocabulary.

**Zero-cost discipline (D-06b):** the block already only runs when `record_degeneracy`; adding one
more `is not None` test inside a block that already never executes during the solve costs nothing.
The hot-path prohibition at `_observability.py:52-59` is preserved. **This is directly unit-testable
— see Validation Architecture.**

---

## The Two Post-Solve Call Sites

Both are dedicated `compute_residuals(result.x, *cost_args, ...)` evaluations whose only purpose is
counting. Verified verbatim:

| Site | File:line | Already passes | Holds stage? |
|------|-----------|----------------|--------------|
| Stage 3 pass 1 | `interface_estimation.py:617-622` | `invalid_count_out=`, `degeneracy_breakdown_out=` | **Yes** — `resolved_discard_stage`, computed at `:371-378` |
| Stage 3 pass 2 | `refinement.py:429-434` | `invalid_count_out=`, `degeneracy_breakdown_out=` | **Yes** — `resolved_discard_stage`, computed at `:203-210` |

`resolved_discard_stage` is already validated against `DISCARD_STAGES` (raising on an unknown value),
so the stage stamped onto a detail row inherits the closed-vocabulary guarantee for free.

**Cost of a new sink argument at these sites:** one new keyword argument, one `list` allocation, and
a `for row in details: row["stage"] = resolved_discard_stage` loop (or a list-comprehension stamp)
before appending into the caller's own out-parameter. Both functions already accept
`discard_stats_out: dict[str, int] | None`; the natural sibling is
`degeneracy_details_out: list[dict] | None = None`, defaulted `None` at both `optimize_interface`
(`interface_estimation.py:294`-region signature) and `joint_refinement` (`refinement.py:101`-region
signature).

**Plumbing chain to reach a real run (all five sites verified):**

```
CalibrationConfig.<new flag>  (schema.py, beside save_conditioning at :362)
   └─ load_config: internals = data.get("internals", {})  (pipeline.py:385-390)
        └─ CalibrationConfig(...)                          (pipeline.py:395-433)
             └─ pipeline.py:1013 _run_stage3()  ->  optimize_interface(..., discard_stage="stage3_interface_optimization")   [:1033]
             └─ pipeline.py:~1283 intrinsic pass ->  joint_refinement(..., discard_stage="stage3_intrinsic_pass")            [:1283]
```

**Complete `discard_stage=` call-site inventory (do not miss one):**

| File:line | Stage |
|-----------|-------|
| `pipeline.py:156` | `stage3_interface_optimization` (the `_calibrate_from_detections` helper) |
| `pipeline.py:1033` | `stage3_interface_optimization` (main `_run_stage3` closure; also used by the outlier-rejection re-run at ~:1187) |
| `pipeline.py:1283` | `stage3_intrinsic_pass` |
| `datasets/pipelines.py:171` | `stage3_interface_optimization` (`calibrate_synthetic` — E1/E4/E5/E6/E7's path) |
| `datasets/pipelines.py:206` | `stage3_intrinsic_pass` (`calibrate_synthetic`) |

Note `pipeline.py:1033`'s closure is invoked **twice** when `reject_outlier_frames` fires (the
re-run at ~:1187 reuses `_run_stage3`), so the same stage label is bumped twice in one run. This is
already true of the Phase 24 counters — it is exactly why the total is a **cross-stage sum with
possible double counting** (CONTEXT § Deferred). The detail sink inherits the same property, which
is fine: the per-observation rows are what makes the distinct count recoverable later, in Phase 29.

---

## The Config Flag Path (D-09)

**Correction to CONTEXT.md:** the class is **`CalibrationConfig`**, not `PipelineConfig`. Verified —
`grep -rn "class PipelineConfig" src/aquacal/` returns nothing;
`src/aquacal/config/schema.py:217` declares `class CalibrationConfig`. The `loss_scale` line
reference (`schema.py:335`) in D-19 is correct; only the class name is wrong. Non-blocking, but the
planner should write `CalibrationConfig` in every task.

**The seam, exactly:**

1. **Field:** `schema.py`, in the `save_*` / `benchmark_*` observability cluster at `:358-364`
   (immediately after `benchmark_memory: bool = False` at `:364` is the natural slot). Add the
   matching `Attributes:` docstring entry in the block at `:295-315`.
2. **YAML parse:** `pipeline.py:385-390`, the `internals = data.get("internals", {})` block. One
   line: `log_all_observation_depths = bool(internals.get("log_all_observation_depths", False))`.
3. **Constructor:** `pipeline.py:~425`, beside `benchmark_memory=benchmark_memory`.
4. **Thread to the residual call:** `pipeline.py:1013` `_run_stage3` closure and the `:1283`
   intrinsic-pass call.

**Suggested key name:** `log_all_observation_depths` — it says what it does (`h_q` for every
observation, not just flagged ones) without leaking a bucket name, and reads correctly under
`internals:` in YAML. Discretionary per CONTEXT.

**E2 reaches it through `config_paper.yaml`** (verified present at
`aquacal_data/real-rig/real-rig/config_paper.yaml`), which today has **no `internals:` block at all**
— the block must be added. That file is inside the downloaded dataset cache, **not** in git. Two
consequences the planner must handle:

- Editing the cached copy is not version-controlled. For the D-01/D-03 probe, **copy
  `config_paper.yaml` into the probe directory, add the `internals:` block there, and run against
  the copy** — but note the config's video paths are relative, so the run still has to `cd` into the
  archive root. The cleanest form is: copy the *modified* config back into the archive root under a
  distinct name (e.g. `config_paper_instrumented.yaml`) and commit that same file into
  `.planning/probes/2026-08-17-degeneracy-classification/` as the provenance record.
- `output_dir: output` in that config is **relative to the archive root**, so
  `diagnostics.json` and the new sidecar land in
  `aquacal_data/real-rig/real-rig/output/`, **not** in E2's `--out`. See § E2 Run Mechanics.

---

## The Sidecar's Home (D-08)

`diagnostics.json` is written by `save_diagnostic_report`
(`src/aquacal/validation/diagnostics.py:844-854`), called from `pipeline.py:1619-1626` with
`config.output_dir` and `discard_stats=dict(discard_stats)`.

Its signature already has the exact precedent shape for a new payload:

```python
def save_diagnostic_report(
    report, calibration, detections, output_dir,
    save_images=True, auxiliary_reprojection=None,
    timings=None, frame_rejection=None, discard_stats=None,
) -> dict[str, Path]:
```

**Two viable placements:**

| Option | Where | Pros | Cons |
|--------|-------|------|------|
| **A (recommended)** | New `degeneracy_details: list[dict] \| None = None` parameter on `save_diagnostic_report`; it writes `output_dir/degenerate_observations.csv` when the list is non-empty | Mirrors `discard_stats` exactly; the function already returns a `dict[str, Path]` of written files, so the new path is discoverable; one call site to change (`pipeline.py:1619`) | Puts a CSV writer in a module that mostly writes JSON + PNGs (it already writes `depth_errors.csv`, so this is precedented) |
| B | `pipeline.py` writes it directly after the `save_diagnostic_report` call | No signature change | Two places now decide what goes next to `diagnostics.json` |

Option A also cleanly satisfies "written only when at least one flagged row exists" — the `if not
degeneracy_details: return` guard lives with the writer.

**Note:** the writer that ordinary users get (library-side, `diagnostics.py`) and the classifier
(experiments-side, `_degeneracy.py`) are **different writers by D-06**. The library sidecar carries
raw geometry + `nan_reason` **codes**; the experiments classifier reads that CSV (or the in-memory
list) and produces the bucketed table. Do not merge them.

---

## Row Cap and Truncation Stamps (D-10)

**Finding: this repo has NO existing CSV header/metadata convention for provisional or truncation
stamps.** Verified by reading `experiments/_io.py::write_experiment_csv` (`:241-292`) — it writes a
bare `df.to_csv(path, index=False)` with no comment lines, no metadata rows, and no sidecar. Every
committed CSV in `experiments/results/` starts with a bare header row (confirmed:
`head -2 experiments/results/exp1_band.csv`).

Existing provenance mechanisms, and why each does/doesn't fit:

| Mechanism | Used by | Fit for D-10 |
|-----------|---------|--------------|
| A separate `*_provenance.json` sidecar | `e1_seed_band_provenance.json`, `e5_/e6_/e7_` equivalents | Good for the *experiments* table; **fails D-10's "a reader of the file alone"** requirement |
| A free-text column repeated on every row | `e7_focal_standoff.csv::scope` (FIX-04) | **Best fit.** Self-contained, survives `pd.read_csv`, and is this repo's own established precedent |
| A leading `#` comment line | nowhere | **Rejected** — would break `pd.read_csv` in `compare_experiment_csv` and every consumer |

**Recommendation:** follow FIX-04. Give both the library sidecar and the classifier table a
`provenance` (or `scope`) free-text column, identical on every row, carrying: the git sha, the
`provisional` marker (D-03), `truncated=true|false`, and the **true** aggregate count from the Phase
24 counters when truncated. Cost: a few hundred bytes per row on a ≤50k-row table; zero new
machinery; and `pandas` reads it unchanged.

The row cap itself is a `len(details) >= ROW_CAP_PER_STAGE` check inside the append (constant of
order 50_000, module-level in `_optim_common.py`), plus one `warnings.warn` on the transition.
**The aggregate count is never derived from `len(rows)`** — it comes from
`degeneracy_breakdown_out["..."]`, which the same pass already computes independently. That
independence is what makes D-10's "keep the count exact" claim true, and a unit test should assert
it directly (truncate at cap=3 with 10 flagged points; assert the breakdown still reports 10).

---

## E1 Band Harness — Exact Nesting (BAND-01)

### The current structure

`experiments/e1_refractive_comparison.py`:

| Symbol | Line | Role |
|--------|------|------|
| `SCENARIO_NAME = "realistic"` | `:150` | E1's production preset |
| `TEST_DEPTHS` (8 depths) | `:151` | the depth sweep |
| `MODELS` (2) | `:156` | refractive / non_refractive |
| `BAND_KEY_COLUMNS = ["seed", "test_depth_m", "model"]` | `:250` | **must gain `noise_std`** |
| `PARAMETER_BAND_KEY_COLUMNS = ["seed", "camera", "model"]` | `:256` | **must gain `noise_std`** |
| `_run_one_model(scenario, n_water, seed)` | `:426` | the single solve; all four callers reach the solver through it |
| `merge_band_columns(df_exp2, df_exp3)` | `:490` | EXP2/EXP3 merge; `test_duplicate_key_raises` already exists for it |
| `scenario.noise_std` passed to test-set detections | `:605` (inside `_build_dataframes`) | **D-11's free ride** — confirmed |
| `_run_band(seeds, out_dir, smoke, force)` | `:958` | the band entry point |
| `_runner(seed)` closure | `:1012` | one seed: `create_scenario` → both models → `_build_dataframes` → `merge_band_columns` |
| `run_seed_band(_runner, seeds)` | `:1046` (defined `experiments/_io.py:166-217`) | calls `_runner` once per seed, stamps `seed`, concatenates |
| `exp1_band.csv` write | `:1048-1055` | `key_columns=BAND_KEY_COLUMNS`, `force=True` |
| `exp1_parameter_band.csv` write | `:1064-1074` | `key_columns=PARAMETER_BAND_KEY_COLUMNS`, `force=True` |

**Note:** CONTEXT.md cites `:438` for the `scenario.noise_std` pass-through. The actual line at
`2a6aed2` is **`:605`**, inside `_build_dataframes`'s per-depth loop
(`generate_synthetic_detections(..., noise_std=scenario.noise_std, seed=depth_seed)`). The
*substance* of D-11 is confirmed and unaffected — overriding `scenario.noise_std` before the solve
does reach the evaluation set for free. Only the line number drifted.

### Where the noise loop nests

`run_seed_band` **cannot** grow a second axis: its signature is shared with E7
(`_io.py:196-211` states this explicitly) and its contract is "call `runner(seed)` once per seed,
stamp `seed`, concatenate". D-12 keeps the axis inside `_run_band`. Two placements:

| Placement | Shape | Verdict |
|-----------|-------|---------|
| **Inside `_runner`, wrapping the two-model loop** | `_runner(seed)` returns 4× rows, each block stamped `noise_std`; concatenated by `run_seed_band` as today | **Recommended.** `run_seed_band` untouched, `exp1_frames` accumulation untouched in structure, one nesting level added at `e1_refractive_comparison.py:~1017` |
| Outside, looping `run_seed_band` four times | Four calls, then `pd.concat` | Also works, but the `last_*` accumulators and the benchmark payload ("taken from the LAST seed") become ambiguous across four calls — avoid |

The override itself is one line inside `_runner`, immediately after
`scenario = create_scenario(scenario_name, seed=seed)` at `:1016`:

```python
scenario.noise_std = noise            # D-11: no create_scenario signature change
```

Then both `_run_one_model` calls and `_build_dataframes`'s test-set generation see it.

**Level set (locked, from the BAND-01 todo):** `NOISE_LEVELS = [0.25, 0.5, 0.82, 1.2]`. 0.5 px must
stay — it reproduces the committed baseline and E1's `--check` bar.

**Do NOT stamp `noise_std` in `run_seed_band`.** It knows nothing about noise; the stamp belongs to
`_runner`'s inner block, before it returns.

### The 640-row reconciliation — CONTEXT.md's number is CORRECT

Measured directly from the committed artifacts:

| Artifact | Committed rows | Arithmetic | With 4 noise levels |
|----------|----------------|-----------|---------------------|
| `exp1_band.csv` | **160** (161 lines − header) | 10 seeds × 8 depths × 2 models | **640** ✓ matches CONTEXT.md |
| `exp1_parameter_band.csv` | **240** (241 lines − header) | 10 seeds × 12 cameras × 2 models | **960** ⚠ CONTEXT.md does not mention this |

So the "640-row count" for the hand-verification sheet is right for `exp1_band.csv`. But the sheet
must **also** record `exp1_parameter_band.csv` going 240 → 960, which no committed document
currently anticipates.

### PITFALL B1 — the key contracts break (HIGHEST RISK IN THIS PHASE)

`write_experiment_csv` (`_io.py:273-292`) validates only that `key_columns` **exist**; it does
`sort_values(by=key_columns, kind="stable")` and writes. **It does not check uniqueness.** So a
naive noise axis produces:

- `exp1_band.csv`: 4 rows sharing every `(seed, test_depth_m, model)` triple. Sorted stably, they
  appear in noise-loop order — deterministic but *undeclared*.
- `exp1_parameter_band.csv`: 4 rows sharing every `(seed, camera, model)` triple, and this file has
  **no** depth column to disambiguate them at all.

Downstream, `compare_experiment_csv` (`_io.py:332-357`) **"Aligns the two frames on `key_columns`
before comparing"** and its documented totality contract explicitly enumerates *"a duplicate key"*
as a failure it must report. E1's `--check` path and any future band `--check` would fail — loudly,
which is the good outcome, but only if someone runs it.

**Required fix (recommend as a hard acceptance criterion):**

```python
BAND_KEY_COLUMNS = ["seed", "noise_std", "test_depth_m", "model"]
PARAMETER_BAND_KEY_COLUMNS = ["seed", "noise_std", "camera", "model"]
```

This is a **tension with the letter of D-12** ("Only `exp1_band.csv` gains the column"). The
resolution: D-12's intent, read against its own rationale and the BAND-01 todo's "Do not" list, is
to protect the three **fixed-contract** CSVs read byte-for-byte by the external figures repo —
`exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`, `exp3_xy_vs_z_anisotropy.csv`.
`exp1_parameter_band.csv` is not one of those; it is a band artifact created by D-19.4-14 in the
same phase and under the same "band CSVs gain columns" precedent. It also *cannot* be left alone,
because `_run_band` writes it unconditionally from the same accumulator. Flag this to the user for
confirmation, but treat "add `noise_std` to both band CSVs and both key lists" as the working
assumption. **See Open Question 1.**

### PITFALL B2 — the smoke-scale band test quadruples

`tests/unit/test_e1_band_mode.py` has real-solve tests at smoke scale
(`test_band_csv_written_at_smoke_scale`, `test_band_csv_carries_exp3_columns`,
`test_parameter_band_csv_carries_exp1_columns`, `test_band_mode_does_not_write_single_seed_csvs`,
and four more, all `tmp_path`-based). If the noise loop runs unconditionally, every one of them runs
4× the solves.

**Recommendation:** in `_run_band`, when `smoke` is true, use a single-element noise list (the
scenario default), mirroring how `depths = [1.30] if smoke else None` already collapses the depth
sweep at `:993`. Add one dedicated non-smoke unit test that asserts the *shape* (640 rows, `noise_std`
present, four distinct values) using a monkeypatched `_run_one_model`, rather than paying for real
solves.

### Cost — the run is ~7 hours, not ~1.8

| Source | Value |
|--------|-------|
| `experiments/results/e1_seed_band_provenance.json` → `"seconds"` | **6319.672 s** for the committed 10-seed band |
| Per band cell (1 seed, 2 models, 8-depth eval sweep) | ≈ **632 s** |
| CONTEXT.md D-19's "400 s of solver time" | *solver only*, single seed — excludes detection generation, the depth sweep, and reconstruction |
| **4 noise levels × 10 seeds = 40 cells** | **≈ 25,280 s ≈ 7.0 h** |

The environment block in that same sidecar records the measuring machine: 20 logical cores, 16.86 GB
RAM, Windows 11, numpy 2.4.2, scipy 1.17.0, OpenCV 4.13.0 — i.e. **this machine**, so the estimate
transfers. The DEGEN-04 todo independently says "E1's 40 runs", confirming the 40-cell shape.

**Planning consequence:** this is a CLAUDE.md long run. Orchestrator only, `nohup` + `disown`,
unbuffered. Never dispatch it to an executor. Combined with the E2 run (48–87 min), the phase has
**two** orchestrator-owned detached jobs; sequence them so neither competes for the 16 GB of RAM
(E2 peaks at ~10.26 GiB).

### The D-14 header site

The existing demotion note lives at **`e1_refractive_comparison.py:56`**, inside the module
docstring:

> ``carries NO accuracy claim (D-19.3-17 demoted it)** -- this band exists for``

A second occurrence at `:1110` is inside the `e1_seed_band_provenance.json` `scope` string
("...neither asserts nor denies an accuracy claim for E1 (D-19.3-17 already demoted E1's own)").
D-14's stated-domain sentence goes **beside `:56`, in the module docstring** — that is "the header".
Whether the `:1110` provenance `scope` string is also updated is a judgment call; updating it would
change `e1_seed_band_provenance.json`'s content on the next band run, which is happening anyway.
Recommend updating both, so a reader of the artifact and a reader of the source meet the same
sentence.

---

## The `optimality` Labelling Target (D-17)

### Where the number ships

| Artifact | Emitter | Line |
|----------|---------|------|
| `benchmark_grid.csv` | `GRID_COLUMNS` list entry | `e4_benchmark_grid.py:520` |
| (null fallback) | `_NULL_METRICS` | `:562` |
| populated from aggregate | `_build_synthetic_row` | `:1290` (`_get(row, f"{_STAGE1}.optimality")`) |
| populated from pipeline record | real-rig row builder | `:1369` (`stage1.get("optimality")`) |
| `benchmark_grid.tex` | `write_grid_latex` | `:1553-1598` |

**It is NOT in `GRID_SUMMARY_COLUMNS`** (`:571-579`) — so it reaches the manuscript's *supplement*
full grid and the real-rig anchor block, not the compact main-text table. Verified against
`experiments/results/benchmark_grid.tex`, whose first block's header row lists only the seven summary
columns.

**Also unflagged elsewhere (CONTEXT.md does not mention this):** the same column ships in
`experiments/results/generalization_sweep.csv` and `generalization_sweep_band.csv` from
`e6_generalization_sweep.py`. If the caveat is worth attaching in E4, it is worth a pointer in E6.
Recommend at minimum a code comment in E6's column list referencing the E4 caveat and the probe.
Flag as scope for the user; do not silently expand.

### The FIX-04 precedent, exactly

FIX-04 (`23-03-PLAN.md:93`, `:346-410`) labelled E7's vacuous rows by **reusing an existing free-text
column** (`e7_focal_standoff.csv::scope`) — **no schema change**, a same-row reason, verified by
inspection and unit test, shipped as its own commit. The current `scope` values (read from disk) are
one long sentence per row naming the re-analysis, its source artifact, its bound, and the decision
ID.

**`benchmark_grid.csv` has no equivalent free-text column** — the closest is `status_reason`, which
is semantically owned by the cell-status gate and must not be co-opted. So the FIX-04 pattern maps
onto E4 as follows:

| Surface | Mechanism | Confidence |
|---------|-----------|------------|
| `benchmark_grid.tex` | **Add a `%` comment block** to the `blocks` list in `write_grid_latex` (`:1587-1597`), which already emits three such comment lines. Free, no schema change, ships to Zenodo inside the artifact. **This is the closest true analogue of FIX-04.** | HIGH |
| `benchmark_grid.csv` | An inline **code comment** on the `GRID_COLUMNS` entry at `:520` (the file already carries a multi-line comment on `degenerate_observations_at_solution` at `:524-530` — exact precedent), plus the module docstring | HIGH |
| A `#` comment line in the CSV itself | **Rejected** — breaks `pd.read_csv` in `compare_experiment_csv` and E4's own `--check` | HIGH |
| The manuscript record | An MF entry (next number: **MF-21**; `MANUSCRIPT-FINDINGS.md` currently ends at MF-20 at `:2047`) | HIGH |

### The caveat's content (from CONTEXT § Specific Ideas, already settled)

Three properties, all from `.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md`:
volatile at a fixed solution (92.78 → 2.16 across restarts, 43×); not comparable across parameter
blocks (three Coleman-Li regimes: `v = 1` unbounded, `v ≈ 700` wide-bounded intrinsics,
`v ≈ 2e-12` pinned); magnitude-dependent in reliability (large values trustworthy — 92.78 real to
5 s.f.; small ones not — 0.001146 against a 3-point reference of 0.001655, 44% disagreement), so
**differences between two small optimality values carry no information**.

---

## D-18 is ALREADY DONE — verify, do not implement

**Finding (HIGH confidence, verified by grep + git log):** all four supersession headers exist,
landed in commit **`02fe224`** — *"docs(23): correct the falsified optimality mechanism in four phase
artifacts"*.

| D-18 target | Falsified text still at | Correction header at | Cites the probe? |
|-------------|------------------------|---------------------|------------------|
| `23-VALIDATION.md:72-74` | `:72-74` ✓ | **`:76`** `> **CORRECTED 2026-08-17 (post-phase)...` | ✓ `.planning/probes/2026-08-17-optimality-decomposition/` |
| `23-RESEARCH.md:76` | `:76` ✓ | **`:84`** `> **CORRECTED 2026-08-17 (post-phase), by three probes in` | ✓ `:85` |
| `23-01-PLAN.md:103` | `:102-108` ✓ | **`:111`** `> **CORRECTED 2026-08-17 (post-phase, plan executed and verified).**` | ✓ `:113` |
| `23-01-SUMMARY.md:153` | `:150-158` ✓ | **`:163`** `> **CORRECTED 2026-08-17, same day, after this summary was committed.**` | ✓ `:184` names DEGEN-05 |

All four line refs in CONTEXT.md resolve to the falsified pin-mechanism text, as stated. The headers
sit immediately after the falsified paragraph in each case (an inline blockquote), rather than at
the top of the file.

**The `19.1-E2-FRAMESET-PROVENANCE.md` precedent format** (its actual first lines, verbatim):

```
> **SUPERSEDED as a description of the current archive — 2026-08-17 (FIX-06, phase 23).**
> Everything below is **correct as history** and is deliberately left intact.
>
> [what the document described] ... [what is now true] ... [where the current answer lives]
>
> Corrected in the same pass: [adjacent citations that were also fixed]
```

That is a **whole-file** header (line 1, followed by `---`). The Phase 23 four use a **paragraph-
local** variant with the same blockquote + bolded-dateline shape. Both are the same pattern applied
at different granularity; the paragraph-local form is arguably better here, because only one claim
in each document was falsified.

**Planning consequence:** D-18 becomes a single verification step, not a task:

```bash
grep -c "CORRECTED 2026-08-17" \
  .planning/phases/23-experiment-correctness-fixes/23-VALIDATION.md \
  .planning/phases/23-experiment-correctness-fixes/23-RESEARCH.md \
  .planning/phases/23-experiment-correctness-fixes/23-01-PLAN.md \
  .planning/phases/23-experiment-correctness-fixes/23-01-SUMMARY.md
# each must be >= 1
```

Record in the SUMMARY that D-18 was satisfied by `02fe224` before this phase opened.

---

## The Gate-Scope Rationale Sites (D-04)

Three text-only insertion points. All verified.

| Site | File:line | What is there now |
|------|-----------|-------------------|
| Vocabulary / rule commentary | `_observability.py:37-84` — the "Discard accounting" and "Degeneracy split vocabularies" comment blocks; `_DISCARD_STAGES` at `:100`; `DISCARD_KEYS` at `:108` | The hot-path prohibition and the two-marginals rule. The authored-vs-given rationale belongs in a new comment block here, near `_DEGENERACY_CAUSES` (`:88`) |
| E4 guard block | `e4_benchmark_grid.py:947-961` — `n_degenerate = discard_stats.get(...)`, `if n_degenerate > 0:` + `logger.warning(...)`, with a D-19.3-11 comment already explaining the smoke carve-out | Add the authored-vs-given paragraph to that existing comment |
| E6 guard block | `e6_generalization_sweep.py:1098-1124` — the three-branch smoke / degenerate / ok gate, each with its own D-19.3-11 comment | Same |

Note the E4 gate is applied downstream in `build_grid_dataframe` (per the `:949-954` comment), and
the E6 gate is applied inline. Both hold D-05's exact `count > 0 -> degenerate` rule with a
smoke-only carve-out. **Do not touch the predicate; only add commentary.**

---

## E2 Run Mechanics (D-01/D-03)

### Data availability: PRESENT ✓

| Check | Result |
|-------|--------|
| `get_cache_info()` | `{'cache_dir': 'C:\\Users\\tucke\\PycharmProjects\\AquaCal\\aquacal_data', 'cached_datasets': ['real-rig'], 'total_size_mb': 4159.69}` |
| `config_paper.yaml` | `aquacal_data/real-rig/real-rig/config_paper.yaml` ✓ (a second copy exists at `Desktop/Aqua/AquaCal/gate1_scratch/real-rig/` — **do not use it**; the cache copy is what `load_example` resolves) |
| Archive contents | `config_paper.yaml`, `config_quickstart_not_paper.yaml`, `extrinsic/`, `intrinsic/`, `reference_calibration.json`, `reference_outputs/` |
| OpenCV | **4.13.0** ✓ — matches D-01's required pin (198 at 4.13, 194 at 4.14). Python 3.12.12, conda-forge. **Do not upgrade cv2 before this run.** |
| Size | 4.16 GB — no download needed |

**D-01's premise holds. The run is possible on this machine today.** This is the single biggest
"could have blocked the phase" risk and it is clear.

### Expected wall clock and memory

The archive's own config header states: *"Expected runtime : ~50 minutes on a modern desktop /
Expected peak RAM : ~11 GiB -- give this run the machine to itself"*. CLAUDE.md's measured range is
**48–87 min**, peak **10.26 GiB** on the 13-camera rig. Against 16.86 GB total RAM, this run must
not overlap the E1 band.

Config shape confirming it is the §3 frameset: 12 primary + 1 auxiliary fisheye (`e3v8250`),
`frame_step: 1`, `max_calibration_frames: 200`, `refine_intrinsics: true`,
`refine_auxiliary_intrinsics: true`, `normal_fixed: false`, `holdout_fraction: 0.2`,
`initial_water_z: 1.0` for all 13.

### The `--out` trap (IMPORTANT for D-03)

`e2_real_rig.py`'s `--out` controls only **E2's own six artifacts**. The calibration's
`output_dir` comes from the YAML (`output_dir: output`), resolved relative to the archive root
because `_run_real_calibration` (`e2_real_rig.py:534-621`) `os.chdir`s into it for the duration of
the `run_calibration` call.

So with `--out .planning/probes/2026-08-17-degeneracy-classification/`:

- E2's six artifacts → the probe dir ✓
- `diagnostics.json` + the new `degenerate_observations.csv` sidecar →
  `aquacal_data/real-rig/real-rig/output/` ✗

**The plan must include an explicit copy step** moving `output/degenerate_observations.csv` (and,
if the D-09 flag is on, the full-population table) into the probe directory before classification.
Otherwise D-03's "nothing lands in `experiments/results/`" is satisfied but the artifact the phase
exists to produce is left in the gitignored dataset cache.

`--config` path: `e2_real_rig.py` accepts `--config <path>`; the branch at `:558-586` resolves it,
`chdir`s to `config_path.parent`, runs, then reads `cfg.output_dir` relative to that root. So
pointing `--config` at an instrumented copy placed **inside the archive root** works cleanly; a copy
placed in the probe dir would break the relative `intrinsic/`/`extrinsic/` paths.

### Recommended invocation (orchestrator only)

```bash
mkdir -p .planning/probes/2026-08-17-degeneracy-classification
nohup python -u -m experiments.e2_real_rig \
  --config aquacal_data/real-rig/real-rig/config_paper_instrumented.yaml \
  --out .planning/probes/2026-08-17-degeneracy-classification \
  --force \
  > .planning/probes/2026-08-17-degeneracy-classification/e2_instrumented.log 2>&1 &
disown
```

Poll the log; do **not** hand this to an executor. Verify liveness via the process listing before
concluding a quiet log means a dead run (memory: quiet-subagent-transcript-is-not-a-dead-run).

### Sizing sanity check (from the DEGEN-04 todo, `:186-201`)

| Hook | Calls per stage | E2 rows | Suite worst case |
|------|-----------------|---------|------------------|
| **post-solve at `result.x`** (the chosen hook) | 1 | **~198 total** | ~198 |
| inside the FD-evaluated cost fn | ≈ 800 | ~160k | **~480M rows, tens of GB** |

Post-pin (FIX-01), the entire suite's flagged population is E2's ~198: the `water_z` pin zeroes E1's
non-refractive arm, the P1 probe measured zero on E1's refractive arm at **every** noise level
including 1.2 px, and E5/E6/E7 record zero in every committed artifact. **The row cap will not be
hit on any planned run** — it exists purely for the pathological-overnight case.

> ⚠ **Do not build against `per_corner_residuals` or `reprojection_residuals.csv`.** They hold 23,028
> observations across 13 cameras including the auxiliary fisheye, which is excluded from Stages 2–3
> entirely. The stage-3 residual vector covers **73,975 observations over 12 cameras**
> (`n_residuals = 147950`). They differ by >3×. Anything built against the exports silently measures
> the wrong population (DEGEN-04 todo `:236-248`).

---

## The `experiments/_degeneracy.py` Shape to Mirror

`write_degeneracy_breakdown(path: Path, breakdown: dict[str, dict], force: bool = False) -> None`
(`experiments/_degeneracy.py`, end of file). Its shape, which the classifier's writer should copy:

1. `path = Path(path)`
2. `if path.exists() and not force:` → `logger.warning("Refusing to overwrite existing ... -- re-run with --force to replace it.", path); return`
3. `path.parent.mkdir(parents=True, exist_ok=True)`
4. write
5. `logger.info("Wrote ... to %s", path)`

Module-level constants to mirror: `DEGENERACY_CAUSES` (3), `DEGENERACY_FATES` (2),
`DEGENERACY_COLUMNS` (6, "in the order every experiment appends them"), and the `None`-means-never-
measured convention (`summarize_degeneracy_columns` docstring). The module docstring itself carries
the two-independent-axes rule — the classifier's docstring should carry the bucket taxonomy in the
same voice.

**The classifier's bucket definitions** (from CONTEXT § Specific Ideas — the precise `h_q` statement
for the docstring): `h_q = Q_z - z_int` is the corner's depth below the **estimated** water surface
in the +Z-down world frame. Positive = submerged. `h_q <= 0` means at or above the interface, so no
refracted path exists and the projector returns NaN tagged `NAN_REASON_ABOVE_INTERFACE`. It is a
statement about the **estimate**, not about reality — both `Q_z` and `z_int` are free parameters, so
solver excursion reaches it too. It is evaluated **at the solution**.

**Pre-registered expectation** (so the finding is falsifiable rather than post-hoc): bucket (a)
should dominate. (c) `h_c <= 0` is dead for E2 by measurement (`h_c` = 1.0472–1.1125 m across all 13
cameras). Obliquity/TIR is refuted twice: `refract_ray` holds the only `sin_t_sq > 1` check and has
**zero callers in `src/`**, and the Newton solve gives θ_w < 48.61° by construction. Positive signal:
`reconstruction_errors.csv` shows **31 of 7,762 validation corners (0.40%) reconstructing up to
51.7 mm above the interface, concentrated in 2 of 52 frames** — right order against 0.27%.

**The four `NAN_REASON_*` constants** (`refractive_geometry.py:29-33`) and their write sites:

| Constant | Value | Branch | Line |
|----------|-------|--------|------|
| `NAN_REASON_NONE` | 0 | (never written; zero-init means this) | — |
| `NAN_REASON_INTERFACE_BELOW_CAMERA` | 1 | whole-batch, `h_c <= 0` | `:663-666` |
| `NAN_REASON_ABOVE_INTERFACE` | 2 | `~valid & ~on_axis`, i.e. exactly `h_q <= 0` | `:690` |
| `NAN_REASON_BEHIND_CAMERA` | 3 | `camera.project()` returned `None` — on-axis (`:702`) and off-axis (`:757`) | `:702`, `:757` |

Bucket (b), "camera-model failure on the crossing point", is precisely `NAN_REASON_BEHIND_CAMERA`
with `h_q > 0` — i.e. the geometry was fine, the pixel was not. That is the tripwire condition in
D-04. The classifier must separate it from bucket (a) by `nan_reason`, not by re-deriving a
predicate from `h_q`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Writing a sorted, resumable experiment CSV | A `to_csv` call | `experiments/_io.py::write_experiment_csv(df, path, key_columns=..., force=...)` | Handles the D-24 resumability guard, `warn_if_overwriting`, stable sort, and the missing-key `ValueError` |
| Comparing a fresh frame to a committed baseline | positional diff | `experiments/_io.py::compare_experiment_csv` | Key-aligned (Pitfall 5), rtol on floats, exact on non-floats, total over duplicate keys and header mismatches |
| Running N seeds and stamping the column | a loop in the script | `experiments/_io.py::run_seed_band(runner, seeds)` | Shared with E7; a divergence here desynchronizes the two scripts |
| Recomputing environment/git provenance per cell | per-cell `capture_environment()` | one call before the loop (as `_run_band:995` already does) | A per-cell `git rev-parse` split an artifact's recorded SHA once already |
| A JSON sidecar writer | `json.dump` inline | `experiments/_degeneracy.py::write_degeneracy_breakdown` shape | Carries the force/refuse-to-overwrite discipline every sibling artifact follows |
| Deriving the aggregate flagged count | `len(detail_rows)` | `degeneracy_breakdown_out["..."]` from the same pass | Truncation makes `len(rows)` wrong; the counters are independent and exact (D-10) |
| Re-deriving a NaN cause at the call site | a predicate on `h_q` | `nan_reason[invalid]` | The projector already assigns exactly one cause per point; a second derivation can disagree |
| Angle-of-incidence for a flagged point | `arctan2(r_p, h_c)` | `arctan2(r_q, h_c + h_q)` (chord) | `r_p` does not exist for flagged points — Newton never ran |

**Key insight:** every mechanism this phase needs already exists in this repo, built and hardened
over Phases 19.x–24. The phase's real work is *placement*, not *construction*. Any new helper is a
signal that an existing one was missed.

---

## Common Pitfalls

### Pitfall 1 — Adding `noise_std` to the CSV but not to the key columns
**What goes wrong:** four rows per key in both band CSVs; `compare_experiment_csv` reports duplicate
keys; the hand-verification sheet's row identity breaks.
**Why it happens:** `write_experiment_csv` sorts by `key_columns` without validating uniqueness, so
the write *succeeds silently*.
**How to avoid:** add `noise_std` to **both** `BAND_KEY_COLUMNS` and `PARAMETER_BAND_KEY_COLUMNS`.
**Warning sign:** `df.duplicated(subset=KEY).any()` is `True`. Make that a unit test.

### Pitfall 2 — Threading the detail sink into `cost_args`
**What goes wrong:** a detail list allocated on every one of thousands of FD residual evaluations;
~480M rows on E1's non-refractive arm; `benchmark.json`'s published wall-clock moves.
**Why it happens:** `cost_args` looks like the natural place for arguments to `compute_residuals`.
**How to avoid:** the D-06b comments at `interface_estimation.py:601-607` and `refinement.py:419-425`
say this explicitly — *"Nothing below is added to `cost_args`"*. Pass at the post-solve call only.
**Warning sign:** a `pytest` assertion counting sink appends during a real solve returns > 2.

### Pitfall 3 — Missing one of the five `discard_stage=` sites
**What goes wrong:** `datasets/pipelines.py:171,206` (the `calibrate_synthetic` path used by every
synthetic experiment) is easy to miss if you only read `pipeline.py`.
**How to avoid:** the five-site table above is exhaustive at `2a6aed2`; re-run
`grep -rn "discard_stage=" src/` as an acceptance check.

### Pitfall 4 — Assuming the sidecar lands in `--out`
**What goes wrong:** the classification input is left in the gitignored dataset cache; the probe
directory looks complete but is not.
**How to avoid:** explicit copy step. See § E2 Run Mechanics.

### Pitfall 5 — Editing the archive's `config_paper.yaml` in place
**What goes wrong:** an uncommitted, untracked edit to a downloaded dataset silently changes what a
"reproduction" run means, and the next `load_example` refresh may clobber it.
**How to avoid:** a named copy (`config_paper_instrumented.yaml`), committed into the probe dir as
provenance.

### Pitfall 6 — Letting an executor run either long job
**What goes wrong:** the Bash tool auto-backgrounds past 600 s and tells the subagent it will be
notified; for a subagent that notification can never arrive. Five of six executors stalled this way
in Phase 19.4.
**How to avoid:** state in each plan, verbatim, which command the executor must NOT run.

### Pitfall 7 — Treating the smoke band's non-zero degenerate count as a failure
**What goes wrong:** E1's `--smoke` `create_scenario("ideal")` legitimately reports 12 flagged
observations (`e1_refractive_comparison.py:~92`). D-05's carve-out exists for exactly this.
**How to avoid:** don't gate smoke. Nothing in E1 compares the count to anything, and it must stay
that way.

### Pitfall 8 — Reading `19.3-ORCHESTRATOR-NOTES.md §4` as ground truth about the `ideal` preset
**What goes wrong:** it compared a solution-state count against a ground-truth statement. The
classifier docstring must say `h_q <= 0` is evaluated **at the solution**, about the **estimate**.

---

## Code Examples

### The existing opt-in out-parameter discipline (the pattern to extend)

```python
# src/aquacal/calibration/_optim_common.py:764, :797-802  (verbatim)
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

### The post-solve call site to extend (both files are identical in shape)

```python
# src/aquacal/calibration/interface_estimation.py:615-622  (verbatim)
invalid_counts: list[int] = []
degeneracy_breakdown: dict[str, int] = {}
compute_residuals(
    result.x,
    *cost_args,
    invalid_count_out=invalid_counts,
    degeneracy_breakdown_out=degeneracy_breakdown,
)
```

`resolved_discard_stage` is already in scope here (computed at `:371-378`), so stamping `stage`
onto the returned rows is local.

### Recomputing the raw geometry at the sink (proposed; all names verified in scope)

```python
# inside the existing `if record_degeneracy:` block in compute_residuals
if degeneracy_details_out is not None:
    z_int = water_zs[cam_name]
    C = camera.C
    idx = np.where(invalid)[0]
    h_q = points_3d[idx, 2] - z_int                       # matches refractive_geometry.py:675
    r_q = np.hypot(points_3d[idx, 0] - C[0],
                   points_3d[idx, 1] - C[1])              # matches :677-679
    h_c = float(z_int - C[2])                             # matches :661
    for k, i in enumerate(idx):
        degeneracy_details_out.append({
            "camera": cam_name,
            "frame_idx": frame_idx,
            "corner_id": int(detection.corner_ids[i]),
            "h_q_m": float(h_q[k]),
            "h_c_m": h_c,
            "r_q_m": float(r_q[k]),
            "chord_incidence_deg": float(np.degrees(np.arctan2(r_q[k], h_c + h_q[k]))),
            "extended": not bool(unextendable[k]),
            "nan_reason": int(nan_reason[i]),
        })
```

> `unextendable` is indexed over `points_3d[invalid]`, i.e. by `k`, while `nan_reason` and
> `detection.corner_ids` are indexed over the full point set, i.e. by `i`. **Mixing the two index
> spaces is the most likely bug in this diff** — pin it with a unit test that constructs a case where
> the flagged points are non-contiguous.

### The `.tex` comment-block seam for D-17

```python
# experiments/e4_benchmark_grid.py:1587-1597  (verbatim, abbreviated)
blocks = [
    "% E4 compact summary (nine synthetic cells, main-text table)",
    summary_path.read_text(),
    "% E4 full grid (nine synthetic cells, supplement table)",
    full_path.read_text(),
    "% E4 real-rig anchor row (pipeline-written, end-to-end; see D-02)",
    real_rig_path.read_text(),
]
```

The caveat is one more `%`-prefixed entry immediately before the two blocks that carry the column.

---

## Runtime State Inventory

*This is not a rename/refactor/migration phase, but the phase does write to state outside the repo,
so the equivalent audit is recorded.*

| Category | Items found | Action required |
|----------|-------------|------------------|
| Stored data | None. No database, no vector store, no external service holds anything this phase renames. Verified: the phase adds columns and files, renames nothing. | None |
| Live service config | None. | None |
| OS-registered state | None — no scheduled tasks, no pm2, no services. | None |
| Secrets / env vars | None. Executors must `export PYTHONPATH="$(pwd)/src"` in worktrees, but that is a session variable, not persisted state. | None |
| Build artifacts / caches | **Yes, two.** (1) `aquacal_data/real-rig/real-rig/output/` will be overwritten by the E2 run — check whether anything there is currently relied on before launching. (2) `experiments/results/exp1_band.csv` and `exp1_parameter_band.csv` are overwritten (`force=True` is implied for band CSVs), so the committed 160/240-row baselines are replaced by 640/960-row files. **Commit the old ones' state / confirm the git diff is intended before the band run.** | Verify + confirm |

**Also noted (housekeeping, not this phase's scope):** `git status` shows two untracked probe
directories from the closed Huber-knee work — `.planning/probes/2026-08-17-huber-knee/e1_control/`
and `e1_treatment/`. Decide whether to commit or gitignore them before the phase's first commit, so
the phase's diffs stay clean.

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | everything | ✓ | 3.12.12 (conda-forge) | — |
| OpenCV (`cv2`) | E2 run; D-01 pins **4.13** | ✓ | **4.13.0** ✓ exact pin | none — do not upgrade |
| numpy | everything | ✓ | 2.4.2 | — |
| scipy | solver | ✓ | 1.17.0 | — |
| pandas | band CSVs | ✓ (band artifacts read cleanly) | — | — |
| `real-rig` dataset (4.16 GB) | D-01's E2 run | ✓ cached at `aquacal_data/real-rig/` | record 21889922 | none |
| `config_paper.yaml` | D-01 | ✓ `aquacal_data/real-rig/real-rig/config_paper.yaml` | — | — |
| RAM | E2 peak ~10.26 GiB | ✓ 16.86 GB total | — | serialize the two long runs |
| Disk | probe artifacts | assume OK (~10 MB full-population table + logs) | — | — |
| git | provenance stamps | ✓ | HEAD `2a6aed2` | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

> **Note on the pytest interpreter (memory: pytest-needs-aquacal-conda-env):** Git Bash `python`
> resolved `cv2 4.13.0` and imported `aquacal.datasets` successfully in this session, so the active
> interpreter is the correct env here. If an executor sees collection errors, it is an interpreter
> problem, not a code problem. Also: this interpreter cannot decode the raw rig AVIs via
> `VideoCapture.read()` — irrelevant here, because the archive ships extracted frames, not AVIs.

---

## Validation Architecture

Test framework detected: **pytest**, `tests/unit/` (one file per source module), `tests/synthetic/`,
`tests/integration/`. Markers include `slow`. `workflow.nyquist_validation` is absent from
`.planning/config.json` ⇒ treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (via the AquaCal conda env) |
| Config | `pyproject.toml` (markers: `slow`) |
| Quick run (per task commit) | `python -m pytest tests/unit/<the touched file> -q` — seconds |
| Full suite (per wave merge / phase gate) | `python -m pytest tests/` — **orchestrator only**, 56–88 min measured |

**`-m "not slow"` is ~26 min and does NOT fit under the 600 s tool ceiling.** Do not give it to an
executor.

### Phase Requirements → Test Map

| Req | Behaviour | Test type | Automated command | Exists? |
|-----|-----------|-----------|-------------------|---------|
| DEGEN-04 | Detail sink appends exactly one row per flagged observation, with correct `(camera, frame_idx, corner_id)` | unit | `pytest tests/unit/test_optim_common.py -k detail_sink -x` | ❌ Wave 0 |
| DEGEN-04 | **Zero-cost discipline:** with `degeneracy_details_out=None`, residuals are bit-identical and nothing is allocated | unit | `pytest tests/unit/test_optim_common.py -k inert -x` | ❌ Wave 0 |
| DEGEN-04 | **Non-contiguous flagged indices** map `unextendable[k]` ↔ `nan_reason[i]` correctly | unit | `pytest tests/unit/test_optim_common.py -k index_spaces -x` | ❌ Wave 0 (**highest-value test in the phase**) |
| DEGEN-04 | Recomputed `h_q`/`h_c`/`r_q` equal the projector's, bit-for-bit | unit | `pytest tests/unit/test_optim_common.py -k recomputed_geometry -x` | ❌ Wave 0 |
| DEGEN-04 | `stage` is present and legal on every emitted row (D-07) | unit | `pytest tests/unit/test_discard_accounting.py -k stage_stamped -x` | ❌ Wave 0 |
| DEGEN-04 | Row cap truncates rows but the aggregate count stays exact; `truncated` stamp present (D-10) | unit | `pytest tests/unit/test_discard_accounting.py -k row_cap -x` | ❌ Wave 0 |
| DEGEN-04 | Classifier buckets each `nan_reason` code to the right named bucket, and (b) is separated from (a) by code not by `h_q` | unit | `pytest tests/unit/test_discard_accounting.py -k classify -x` | ❌ Wave 0 |
| DEGEN-04 | Sidecar is **not** written when zero flagged rows (D-08); written when ≥1 | unit | `pytest tests/unit/test_diagnostics.py -k degenerate_sidecar -x` | ❌ Wave 0 |
| DEGEN-04 | Config flag defaults **off** and round-trips through `load_config` (D-09) | unit | `pytest tests/unit/test_cli.py tests/unit/test_internals.py -k log_all_observation -x` | ❌ Wave 0 |
| DEGEN-04 | The 198 classify to named buckets; bucket (a) dominates | **artifact inspection** — no test | the E2 probe run + `FINDINGS.md` | orchestrator |
| BAND-01 | `exp1_band.csv` has **640** rows, a `noise_std` column, and 4 distinct values | unit (monkeypatched `_run_one_model`) | `pytest tests/unit/test_e1_band_mode.py -k noise_axis_shape -x` | ❌ Wave 0 |
| BAND-01 | **No duplicate keys** in either band CSV under the new key lists | unit | `pytest tests/unit/test_e1_band_mode.py -k no_duplicate_keys -x` | ❌ Wave 0 |
| BAND-01 | `_run_smoke` / `_run_check` / single-seed paths write no `noise_std` and are unchanged (D-12) | unit | `pytest tests/unit/test_e1_band_mode.py tests/unit/test_experiments_e1.py -k "smoke or check" -x` | partially ✓ (extend) |
| BAND-01 | The three fixed-contract CSVs' headers are byte-unchanged | unit | `pytest tests/unit/test_experiments_e1.py -k columns -x` | likely ✓ (verify) |
| BAND-01 | The D-14 stated-domain sentence is present beside the demotion note | unit (source-text assertion, FIX-06 precedent) | `pytest tests/unit/test_experiment_inertness.py -k stated_domain -x` | ❌ Wave 0 |
| BAND-01 | The band's actual numbers at 4 levels | **artifact inspection** — no test | the ~7 h band run + committed CSVs | orchestrator |
| DEGEN-05 | D-18's four correction headers exist | **verification command**, no test | `grep -c "CORRECTED 2026-08-17" <4 files>` | ✓ already satisfied at `02fe224` |
| DEGEN-05 | The `optimality` caveat ships in `benchmark_grid.tex` | unit (source/output-text assertion, FIX-04 precedent) | `pytest tests/unit/test_experiments_e4.py -k optimality_caveat -x` | ❌ Wave 0 |
| DEGEN-05 | The verdict sentence (Huber knee closed, sign + magnitude, probe cited) | **recorded-decision only** — no test | SUMMARY + MF-21 | — |
| D-04 | Gate-scope rationale present at all three sites | unit (source-text assertion) | `pytest tests/unit/test_experiment_inertness.py -k gate_rationale -x` | ❌ Wave 0 |
| D-05 | The synthetic gate predicate is still exactly `count > 0` | unit | `pytest tests/unit/test_experiments_e4.py tests/unit/test_experiments_e6.py -k degenerate_gate -x` | likely ✓ (verify) |

### Sampling rate

- **Per task commit:** the one targeted `pytest tests/unit/<file>.py -q` for the files that task touched.
- **Per wave merge:** the union of the wave's targeted files, run by the orchestrator.
- **Phase gate:** full `python -m pytest tests/` green before `/gsd:verify-work` — **orchestrator, detached**.

### Wave 0 gaps

- [ ] `tests/unit/test_optim_common.py` — 4 new tests for the detail sink (DEGEN-04)
- [ ] `tests/unit/test_discard_accounting.py` — 3 new tests: stage stamping, row cap, classifier (DEGEN-04)
- [ ] `tests/unit/test_diagnostics.py` — 2 new tests for the D-08 sidecar
- [ ] `tests/unit/test_e1_band_mode.py` — 3 new tests, all with `_run_one_model` monkeypatched so no real solve runs (BAND-01)
- [ ] `tests/unit/test_experiments_e4.py` — 1 new test for the D-17 caveat
- [ ] `tests/unit/test_experiment_inertness.py` — 2 new source-text assertions (D-14, D-04)
- [ ] No framework install needed — pytest and the env are present.

### What is explicitly NOT testable

Three deliverables are recorded decisions with no verification criterion, and the plan should say so
rather than inventing one:

1. **The DEGEN-05 verdict sentence** (D-15/D-16/D-19). Nothing to measure; D-19 explicitly says
   *"this is no longer a plan task… there is no measurement to schedule, no artifact to produce, and
   no verification criterion."*
2. **The classification finding itself.** The E2 run produces one table; the interpretation goes in
   `FINDINGS.md`. It is provisional by D-02 and reaches no §3-facing number.
3. **The gate-scope decision (D-04).** A policy call conditioned on the run's dominant bucket. Its
   only checkable artifact is that the rationale text exists at the three named sites.

---

## Security Domain

Assessed. This is a single-user local scientific CLI with no network surface, no auth, no session
management, and no untrusted input path. `experiments/_io.py:220-240` already records the prior
judgment that a `..`-traversal guard is *"disproportionate for a single-user local CLI"`.

| ASVS category | Applies | Control |
|---------------|---------|---------|
| V2 Authentication | no | — |
| V3 Session management | no | — |
| V4 Access control | no | — |
| V5 Input validation | **partially** | The new config key is `bool(...)`-coerced in `load_config`, matching the existing `internals` flags. The new sink's stage label is validated against `DISCARD_STAGES` (raising) by the existing `resolved_discard_stage` code. |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| An unbounded per-observation log fills the disk on an unattended overnight run | Denial of service | D-10's row cap + warning; the sink is off by default and the flagged population is ~198 |
| A truncated table is read as complete | Tampering / denial of evidence | D-10's in-artifact `truncated` stamp; the count comes from an independent counter |
| A provisional count leaks into a published number | Tampering (of the record) | D-02 + D-03's in-header provisional + git-sha stamp; the probe is isolated from `experiments/results/` |
| An untracked edit to the dataset's `config_paper.yaml` silently redefines "reproduction" | Repudiation | Named copy + commit it as probe provenance (Pitfall 5) |

---

## State of the Art

| Old position | Current position | When changed | Impact on this phase |
|--------------|------------------|--------------|----------------------|
| E1's `optimality_intrinsic` = 92.78 is caused by the tight `water_z` pin | The pinned slot contributes **0.00%** (1.95e-11 of 92.78); it is entirely the max **extrinsic** gradient | 2026-08-17, optimality-decomposition probe | D-17's caveat content; D-18 already recorded it |
| E1's non-refractive baseline might be under-converged, caveating the 97–178× ratio | Converged (largest warm-restart cost drop 1.8e-9); **the band is strengthened, not caveated** | 2026-08-17 (D-15, MF-18) | DEGEN-05 verdict |
| The Huber knee is an open fairness objection | **Closed by measurement**: −1.09% at the deepest point, ≤6.83% anywhere, against a ±30% band | 2026-08-17 at `054d753` (D-19) | Removed from the plan entirely |
| Obliquity / TIR is a plausible bucket | **Retired** — `refract_ray` has zero callers in `src/`; θ_w < 48.61° by construction | 2026-08-15 | Not a classifier bucket |
| E1's non-refractive arm flags 14,949 observations | FIX-01's `water_z` pin zeroes it; the suite's whole flagged population post-pin is E2's ~198 | Phase 23 | Row cap will never be hit |
| The published Zenodo archive is frame-subsampled (record 18645385) | Record **21889922**, not subsampled; 262 frames → 210/52 → 200 calibration | 2026-08-12 / `25655f7` | The cached archive IS the §3 frameset |
| `2026-08-15` todo's `198 / 73,975 = 0.268%` | Invalidated — the 198 is a cross-stage sum with possible double counting | Phase 24 | D-04 settles on **mechanism**, never on the count |

**Stale in CONTEXT.md** (both minor, both corrected above): the config class is `CalibrationConfig`,
not `PipelineConfig`; and `scenario.noise_std`'s test-set pass-through is at `:605`, not `:438`.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | Recomputing `h_q`/`h_c`/`r_q` at the `compute_residuals` call site is bit-identical to the projector's values | Detail Sink | Low — same float64 ops on the same inputs; a unit test pins it. If wrong, plumb an out-parameter instead. |
| A2 | `chord_incidence_deg` is an acceptable substitute for D-06's "exit angle" | Detail Sink | Medium — it is a *different* quantity from the refracted angle. Mislabelling it would repeat the class of error MF-17/FIX-04 exists to prevent. **Confirm the name with the user.** |
| A3 | `exp1_parameter_band.csv` may gain `noise_std` despite D-12's letter | E1 Band | **High if wrong** — but the alternative (960 rows with duplicate keys) is strictly worse. See Open Question 1. |
| A4 | The E1 noise band is ≈7.0 h, extrapolated linearly from 6319.67 s / 10 seeds | E1 Band | Low — the arithmetic is 4× a measured wall clock on this machine. Noise level does not change problem size. |
| A5 | `log_all_observation_depths` is a suitable config key name | Config Flag Path | None — explicitly Claude's discretion per CONTEXT |
| A6 | The `%`-comment block in `write_grid_latex` is the right D-17 surface for the `.tex` | Optimality Labelling | Low — it is the only in-artifact free-text surface E4 has, and the function already emits three such lines |
| A7 | `pytest tests/` on this machine is 56–88 min | Validation Architecture | Low — from CLAUDE.md's own measurement; not re-measured this session |
| A8 | E6's `generalization_sweep.csv` also shipping `optimality_...` warrants at least a pointer | Optimality Labelling | Low — scope question, not a correctness question. Flagged for the user rather than assumed into scope. |

---

## Open Questions (RESOLVED)

> **All five resolved during planning, 2026-08-18** — resolution noted under each question,
> citing the plan that settled it. Kept verbatim as the audit trail.

1. **Does `exp1_parameter_band.csv` gain `noise_std`, and do both key lists gain it?** *(blocks BAND-01's plan)*
   - **What we know:** `_run_band` writes both band CSVs from the same per-seed accumulators. With
     four noise levels, `exp1_parameter_band.csv` goes 240 → 960 rows with fully duplicated
     `(seed, camera, model)` keys, and `exp1_band.csv` gets four rows per
     `(seed, test_depth_m, model)`. `write_experiment_csv` does not detect this;
     `compare_experiment_csv` would.
   - **What's unclear:** D-12 says *"Only `exp1_band.csv` gains the column."* That reads as written
     against the three **fixed-contract** CSVs (which must not change and will not), not against
     `exp1_parameter_band.csv`, which is itself a band artifact from the same D-19.4-14 precedent.
   - **Recommendation:** add `noise_std` to both band CSVs and to **both** key column lists. Surface
     this to the user as a one-line confirmation during planning; it is a five-minute answer and a
     silently-broken artifact otherwise. Do not proceed on the literal reading.
   - **RESOLVED (25-04):** taken as recommended — `noise_std` added to **both** `BAND_KEY_COLUMNS`
     and `PARAMETER_BAND_KEY_COLUMNS`; `exp1_parameter_band.csv` goes 240 → 960. The departure from
     D-12's literal text is documented in-source and in 25-04 Task 1, not silent.

2. **`chord_incidence_deg` vs an `exit_angle_deg` NaN column.** The refracted exit angle is
   genuinely unrecoverable for a flagged observation (§ Detail Sink). Recommend the chord angle
   under an unambiguous name; confirm the naming so it is never mistaken for the refracted angle.
   - **RESOLVED (25-01):** the column is `chord_incidence_deg`; `exit_angle_deg` is never emitted,
     because `r_p` does not exist for a flagged point.

3. **Does the D-17 caveat extend to E6's `generalization_sweep.csv`?** Same column, same Zenodo
   destination, not named in D-17. Recommend at minimum a code comment pointing at the E4 caveat.
   User call on whether that is in scope.
   - **RESOLVED (25-05):** minimum action only — a pointer comment in E6's column list referring to
     E4's caveat. Scope not silently expanded.

4. **Where does the D-17 caveat live for `benchmark_grid.csv` specifically?** The `.tex` has a
   comment surface; the CSV has none that survives `pd.read_csv`. Options: (a) code comment +
   module docstring + MF-21 only; (b) a sibling `benchmark_grid_notes.md` shipped with the artifact.
   Recommend (a) plus MF-21 — the CSV's consumers are the `.tex` and the figures repo, both of which
   will meet the `.tex` caveat.
   - **RESOLVED (25-05):** option (a) — code comment + module docstring + MF-21. No sibling notes file.

5. **Sequencing of the two long runs.** E2 (~1 h, 10.26 GiB peak) and the E1 band (~7 h) must not
   overlap on 16.86 GB. Which goes first is a plan-decomposition call: E2 first unblocks D-04's
   gate-scope decision, which is criterion 2; the band unblocks criterion 3. Recommend **E2 first**,
   because D-04's rationale text is downstream of it and the band run can proceed overnight
   afterwards.
   - **RESOLVED (wave graph):** E2 first (wave 3), E1 band last (wave 5), separated by the doc-only
     25-07. The wave barrier guarantees they never overlap on the 16.86 GB machine.

---

## Sources

### Primary (HIGH confidence) — read directly at `2a6aed2`

- `src/aquacal/calibration/_optim_common.py:670-871` — `compute_residuals` signature, `record_degeneracy`, the `if record_degeneracy:` block, the six-key fill
- `src/aquacal/core/refractive_geometry.py:25-33, 596-780` — the four `NAN_REASON_*` constants and all four write sites; `h_c` `:661`, `h_q` `:675`, `r_q` `:679`, `valid` `:682`, Newton loop `:713-741`, `r_p`/`incidence_angle_deg` `:749, :766`
- `src/aquacal/calibration/interface_estimation.py:294-296, 371-378, 610-660` — the post-solve site, `resolved_discard_stage`, the D-06b comment
- `src/aquacal/calibration/refinement.py:101-103, 203-210, 419-460` — the mirrored site
- `src/aquacal/calibration/_observability.py:1-120` — hot-path prohibition, `_DEGENERACY_CAUSES/_FATES`, `_DISCARD_STAGES`, `DISCARD_KEYS`
- `src/aquacal/calibration/pipeline.py:156, 195-433, 1000-1090, 1283, 1590-1640` — `load_config`, the `internals` block, `_run_stage3`, `save_diagnostic_report` call
- `src/aquacal/config/schema.py:217-372` — `CalibrationConfig` (not `PipelineConfig`), `loss_scale` `:335`, the `save_*` cluster `:358-364`
- `src/aquacal/validation/diagnostics.py:844-884` — `save_diagnostic_report` signature and docstring
- `src/aquacal/datasets/pipelines.py:171, 206` — the `calibrate_synthetic` `discard_stage` sites
- `experiments/_degeneracy.py` (whole file) — the writer shape and the two-axes rule
- `experiments/_io.py:166-217, 241-292, 332-380` — `run_seed_band`, `write_experiment_csv`, `compare_experiment_csv`
- `experiments/e1_refractive_comparison.py:56, 150-256, 426-470, 490, 520-620, 958-1110` — the band harness
- `experiments/e2_real_rig.py:79-94, 534-640, 844-935` — the run path, `--config`, `--out`
- `experiments/e4_benchmark_grid.py:515-580, 940-961, 1553-1598` — `GRID_COLUMNS`, the guard block, `write_grid_latex`
- `experiments/e6_generalization_sweep.py:274-282, 1090-1130` — the guard block
- `aquacal_data/real-rig/real-rig/config_paper.yaml` — the E2 config, verified present
- `experiments/results/exp1_band.csv` (160 rows), `exp1_parameter_band.csv` (240 rows), `e1_seed_band_provenance.json` (6319.67 s), `benchmark_grid.tex`, `e7_focal_standoff.csv` (the FIX-04 `scope` column)
- `.planning/phases/23-experiment-correctness-fixes/{23-VALIDATION,23-RESEARCH,23-01-PLAN,23-01-SUMMARY}.md` — D-18 targets, verified already corrected
- `.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md:1-20` — the supersession-header precedent, verbatim
- `.planning/todos/pending/2026-08-15-classify-the-198-unprojectable-observations.md` — the hook-point sizing table, the log-raw-classify-offline rule, the export trap
- `.planning/todos/pending/2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` — the level set, the "Do not" list, the P1 probe table
- `git log`/`git show` — `02fe224`, `2a6aed2`, `054d753`
- Live environment probe — `cv2 4.13.0`, Python 3.12.12, `get_cache_info()`

### Secondary (MEDIUM confidence)

- `.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md` (header + method + Findings table read; not re-derived, per criterion 4)
- CLAUDE.md, `.planning/knowledge-base.md` § Known Issues (executor-stall policy), project memory index

### Tertiary (LOW confidence)

- None. Nothing in this document rests on WebSearch or training data.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Call signatures & line anchors | HIGH | Read directly at `2a6aed2`; two CONTEXT.md drifts found and corrected |
| `h_q`/`r_q`/`h_c` reachability + exit-angle finding | HIGH | Derived from the `valid` mask and Newton loop bounds, read verbatim |
| Config flag seam | HIGH | All five plumbing hops verified, including the two `datasets/pipelines.py` sites |
| E1 band shape & the 640-row reconciliation | HIGH | Computed from committed CSV line counts; arithmetic checks out both ways |
| The key-uniqueness pitfall | HIGH | `write_experiment_csv` source read; `compare_experiment_csv` docstring names duplicate keys explicitly |
| E1 band runtime (~7 h) | HIGH | 4× a measured 6319.67 s on this machine (env block confirms the machine) |
| D-18 already done | HIGH | `grep` + `git log` confirm `02fe224` |
| E2 data availability & cv2 pin | HIGH | Probed live |
| D-17 surface choice | MEDIUM | The `.tex` comment block is a judgment call; the CSV has no clean in-artifact surface |
| Row-cap/truncation convention | MEDIUM-HIGH | Verified that **no** convention exists; the FIX-04 free-text-column recommendation is an inference from precedent, not an existing rule |

**Research date:** 2026-08-17
**Valid until:** this phase only — it is pinned to `2a6aed2` and to a pre-freeze tree. Re-verify any
line anchor after the first commit of Phase 25 lands.
