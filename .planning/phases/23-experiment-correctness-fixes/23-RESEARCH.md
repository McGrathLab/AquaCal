# Phase 23: Experiment Correctness Fixes - Research

**Researched:** 2026-08-17
**Domain:** D-02 probe (pinned + normal-free conditioning) and Nyquist validation architecture
**Confidence:** HIGH (D-02 probe: measured directly, two independent runs). MEDIUM (validation
vehicle mapping for FIX-03/04/06: derived from existing test file contents, not exhaustively
re-verified against every assertion).

This is a narrow, probe-first research pass per the phase mandate. CONTEXT.md is recon-complete;
this document does not re-derive its 11 findings or 14 decisions. It adds exactly one new
measurement (D-02) and the required Validation Architecture section.

## D-02 Probe Result

### What was measured

D-02 requires probing the **pinned `water_z` + normal-free** combination — the configuration
FIX-01 and FIX-02 will jointly produce in E1's non-refractive arm, and the one no existing probe
had reached (pinning did not exist before this session).

**Mechanism used (probe-only):** monkeypatched `build_bounds` at **both** its independent
import sites — `aquacal.calibration.interface_estimation.build_bounds` (stage-3 first pass,
`interface_estimation.py:277`) and `aquacal.calibration.refinement.build_bounds` (stage-3 second
/ intrinsic-refinement pass, `refinement.py:184`). The wrapper calls the real `build_bounds` for
every slot, then overwrites the `water_z` slot's `[lower, upper]` with a degenerate interval
(`1.031 - 1e-12`, `1.031 + 1e-12`). Script:
`.planning/probes/2026-08-17-phase-23-recon/probe_pinned_normal_free.py`.

**This is NOT a faithful stand-in for D-01's production threading.** D-01 specifies a bounds
override reaching `build_bounds` from the experiment (a kwarg/parameter), not a process-wide
monkeypatch of the function object. The probe's mechanism is fine for a single measurement but
must not be copied into `src/`. Flagged explicitly in the probe script's docstring.

### A genuine finding surfaced by the probe, not by recon

The first probe run patched only `interface_estimation.build_bounds` (the site D-01's prose
names). Result: `water_z` correctly held at 1.031 m through the **first** stage-3 pass
(optimality dropped from 7.28 → 1.44, consistent with a bound landing), then **drifted to
0.0425 m** during the **second** (intrinsic-refinement) pass, because that pass imports
`build_bounds` independently at `refinement.py:184` and was not patched. Preserved as
`probe_pinned_normal_free_FIRSTPASS_ONLY_finding.json`.

**Consequence for planning:** FIX-01's implementation must thread the pin to **both** call
sites (`interface_estimation.py:277` and `refinement.py:184`), not one. `_run_one_model`
(`e1_refractive_comparison.py:312`) runs the full two-pass pipeline
(`refine_intrinsics=True`), so the second pass is always exercised for E1's non-refractive arm —
a single-site pin would silently ship a partially-broken fix that looks correct on the first
pass's diagnostics alone. This is new information beyond CONTEXT.md's D-01/D-05 and should be
folded into the FIX-01 plan.

### Result: pinned + normal-free, both passes patched

| Metric | Pinned + normal-free (this probe) | Unpinned + normal-free (FIX-02 alone, existing `probe_normal_fixed.json`) |
|---|---|---|
| `water_z` recovered | **1.030999999999 m** | 0.011959561136834829 m |
| `water_z` error vs GT 1.031 m | **~0.0 mm** (pinned by construction) | −1019.04 mm |
| `degenerate_observations_at_solution` | **0** (corroboration only, D-03) | 0 |
| `cost_interface` (stage-3 pass 1) | 26067.0205835744 | 26067.020584816863 |
| `cost_intrinsic` (stage-3 pass 2) | 15097.612313075724 | 15097.612288746863 |
| `status_interface` / `status_intrinsic` | 2 / 2 | 2 / 2 |
| `optimality_interface` | 1.4445430872830798 | 7.284926295332703 |
| `optimality_intrinsic` | 92.7841140024072 | 49.651241910874205 |
| Terminated on a bound? | **Yes** (`bound_hit: true` — expected and correct: it is pinned by construction) | No (interior-ish; the unpinned FIX-02-alone arm lands at 0.012 m, itself near the 0.01 floor per the D-06 table, but that is a *different*, unpinned run) |
| Wall time | 136.1 s | 138.2 s |

Raw records: `.planning/probes/2026-08-17-phase-23-recon/probe_pinned_normal_free.json`.

**Cost comparison to unpinned:** `cost_interface` matches the unpinned FIX-02-alone baseline to
~9 significant figures (26067.0205835744 vs 26067.020584816863, Δ ≈ 1.3e-6); `cost_intrinsic`
matches to ~9 significant figures as well (Δ ≈ 2.4e-5). This is consistent with — though not
quite as tight as — D-03's reported "identical to 10 significant figures" for FIX-02 alone
against the fully-unpinned baseline. The tiny residual difference here is attributable to the
intrinsic pass's re-solve landing at a slightly different local optimum once `water_z` is held
fixed rather than free to drift toward 0.012 m; it is not evidence of degraded conditioning.

**`optimality_intrinsic` rose to 92.78** (vs 49.65 unpinned, and vs 3.38 in the broken
first-pass-only run). This is an expected artifact of pinning to a ~2e-12-wide interval: the
first-order optimality measure (`scipy.optimize.least_squares`'s projected-gradient KKT
residual) is large exactly *because* the parameter is pinned against a near-zero-width box —
the unprojected component of the gradient along that direction cannot be driven to zero by
definition. It does not indicate a stalled or ill-conditioned solve; `status_intrinsic` still
reports `2` (`ftol` satisfied) and cost matches the unpinned run closely.

> **CORRECTED 2026-08-17 (post-phase), by three probes in
> `.planning/probes/2026-08-17-optimality-decomposition/`.** Two claims in the paragraph above are
> wrong:
>
> 1. **"large exactly *because* the parameter is pinned"** — no. The pinned `water_z` slot
>    contributes **0.00%** of the reported optimality (1.95e-11 of 92.78). scipy's `trf` reports
>    `||g·v||∞` where `v` is the Coleman-Li *distance to the bound*; pinned, that distance is
>    ~1.8e-12, so the slot's contribution is crushed toward zero rather than inflated. The
>    paragraph describes an *unscaled* projected gradient, which scipy does not report. The 92.78
>    is entirely the max **extrinsic** gradient (`v = 1`, unbounded). The raw gradient on the
>    pinned slot genuinely is large (9.75) — that half of the intuition was right — but it never
>    reaches the reported number.
> 2. **"does not indicate a stalled or ill-conditioned solve"** — half right. **Not stalled**:
>    warm-restarting each solve from its own solution recovers no cost (largest relative drop
>    1.8e-9), so the arm is converged and E1's comparison is fair. But it **is** ill-conditioned,
>    severely: optimality swings 92.78 → 27.58 → 2.16 across restarts while cost moves 1.8e-9,
>    implying directional curvature ~3e8.
>
> Not the cause: finite-difference Jacobian error was tested and **falsified** — a
> central-difference Jacobian agrees to five significant figures (92.7841 vs 92.7843), which also
> validates the library's FD step rule.
>
> The **Verdict** section below is unaffected: the pinned + normal-free combination does not
> degrade conditioning, `water_z` recovers to ground truth, and cost is essentially unchanged.
> Only the explanation of the optimality number changes.

### Verdict

**The pinned + normal-free combination does NOT degrade conditioning**, once the pin is threaded
to both `build_bounds` call sites. `water_z` recovers to ground truth (1.031 m) as designed, the
degeneracy guard reads 0 (corroboration, not the test, per D-03), cost is essentially unchanged
from the unpinned solve, and the elevated `optimality_intrinsic` is the expected signature of a
tight pin rather than a conditioning problem. D-02's expectation — that the question is moot — is
confirmed. **The Claude's-Discretion item "the FIX-01 fallback if the pinned + normal-free probe
degrades" is therefore not needed; no fallback policy is required.**

The only actionable output of this probe is the two-call-site finding above, which changes what
"threading the pin" means for the FIX-01 plan — it is not a degradation of the combination itself.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing `tests/unit/` suite) |
| Config file | none dedicated — plain `pytest.ini`/`pyproject.toml` discovery; `python -m pytest tests/` per `CLAUDE.md` |
| Quick run command | `python -m pytest tests/unit/test_experiments_e1.py tests/unit/test_experiments_e4.py tests/unit/test_experiments_e6.py tests/unit/test_e7_focal_standoff.py tests/unit/test_experiments_provenance.py -x` |
| Full suite command | `python -m pytest tests/` (orchestrator-owned; NOT run by this phase) |

### Cheap-tier verification vehicles (D-11 budget, ~6 min)

Per D-11, only FIX-01, FIX-02, and FIX-05's aggregation path have outcomes that cannot be
predicted by reading — these three get runtime probes. FIX-03, FIX-04, FIX-06 are inspection/
unit-test verifiable.

| Req | Verification vehicle | Command | Value that proves it |
|---|---|---|---|
| FIX-01 | E1 non-refractive arm, single seed, `--out experiments/verify_23/` | `python -u -m experiments.e1_refractive_comparison --out experiments/verify_23/` (or the `--seeds 42` band form if the plan prefers) | `water_z` column for the non-refractive row lands at 1.031 m (±numerical noise), not 1.99 m or 0.012 m; `degenerate_observations_at_solution` = 0 (corroboration only, D-03) |
| FIX-02 | Same E1 run (both arms share the invocation) | same command | Both arms' records show `normal_fixed: false` in solver_config/provenance; refractive arm's recovered `water_z` stays close to its established −7.43 mm offset from 1.031 m (not a new large excursion) |
| FIX-05 | E4 smoke cells, `--smoke --out experiments/verify_23/` | `python -u -m experiments.e4_benchmark_grid --smoke --out experiments/verify_23/` | The real-rig E2 benchmark row resolves relative to `--out` (not the hardcoded `E2_BENCHMARK_PATH`) in the aggregated `benchmark_grid.csv` under `experiments/verify_23/`; run `--check` afterward against the same `--out` and confirm the two named exclusions (below) are the *only* mismatches |
| FIX-03 | `tests/unit/test_experiments_e6.py::test_water_z_error_helper` and the E6 schema/no-verdict tests (`test_e6_row_schema`, `test_no_verdict_column`) — inspection + unit test, not a runtime probe per D-11 | `python -m pytest tests/unit/test_experiments_e6.py -x` | Signed, gauge-corrected Z error column present; per-camera decomposition emitted; no new verdict column introduced (E6 stays descriptive) |
| FIX-04 | `tests/unit/test_e7_focal_standoff.py` and `tests/unit/test_e7_band_mode.py` — inspection + unit test | `python -m pytest tests/unit/test_e7_focal_standoff.py tests/unit/test_e7_band_mode.py -x` | `fixed` rows carry the vacuous-by-construction label in the existing free-text `scope` column, not a reported measured verdict |
| FIX-06 | Grep/inspection of the four string sites (`e2_real_rig.py`, `synthetic.py`, plus the fourth site the todo names) — no dedicated test exists; this is intentionally inspection-only per D-11 | `grep -n "60 usable frames\|12 validation\|1,817 comparisons" experiments/e2_real_rig.py src/aquacal/**/synthetic.py` (adapt paths per the plan) | Strings read the verified figures (262 → 52 → 7,762) matching the corrected values, not the stale ones |

### The `--check` exclusion (D-07/D-09)

`--check` is **not** FIX-05's verification vehicle — `_run_check` (`e4_benchmark_grid.py:1836`)
hardcodes `"exit_code": None` at `:1872` because no subprocess runs under `--check`, so that
column is always-red by construction (D-07, D-10). The named exclusion list an implementation
must apply when comparing `--check` output to a committed reference is exactly:

- `exit_code`
- `status_reason`

All other columns (33 of 35 per D-07's 2026-08-17 measurement) are expected to reproduce to
1e-6. FIX-05's real verification vehicle for the aggregation-path fix is the **smoke cells**
table row above, not `--check`.

`_run_check` also has the second call site FIX-05 must cover: `build_grid_dataframe(out_dir,
cell_statuses, E2_BENCHMARK_PATH)` at `e4_benchmark_grid.py:1876` passes the module-level
constant directly, bypassing whatever `--out`-relative resolution the main aggregation path
gets.

**CORRECTION (verified against source 2026-08-17, after this document's first draft).** The second
call site is **`_run_full` (`:1954`)**, not `_run_smoke_cells`. `_run_smoke_cells` (~`:1884`) runs
`SMOKE_CELLS` through `run_cell_subprocess` and returns — it never calls `build_grid_dataframe` at
all, as that function's own comment at ~`:1390` states. The count of two sites that D-09 requires is
unchanged; only the second site's name was wrong.

**This changes what verification means for FIX-05:** `--smoke` does not exercise the aggregation
path, so it cannot verify the fix. Using it as the acceptance vehicle would be a step that passes
whether or not the fix works — the same pathology as the always-red `--check` FIX-05 is fixing.
FIX-05's vehicles are the `tmp_path` unit tests (which drive `build_grid_dataframe` and both
callers' resolution directly, in seconds) plus the read-only `--check` corroboration.

### Sampling rate

- **Per task commit** (FIX-01/02 plan): quick run command above, scoped to the touched test
  files.
- **Per wave/plan merge**: the three cheap-tier runtime probes (E1 full, E4 `--smoke`, then
  `--check` against the same `--out` to confirm only the two named columns differ).
- **Phase gate**: cheap tier green, quick pytest subset green, before `/gsd:verify-work`. The
  E4 nine-cell grid, E1's 10-seed band, and the full `pytest tests/` suite are explicitly
  **out of phase** (Phase 28) per D-11 — do not run them here even as a "just to be safe" check.

### D-12: output location

Every in-phase verification run writes to a dedicated, git-ignored `--out` directory —
`experiments/verify_23/` is the suggested name (matches D-12's example). Confirm it is
git-ignored (or add it) before running; because these artifacts are never committed, any
evidence a verification run produces that is worth keeping (e.g. the FIX-01 recovered `water_z`,
the FIX-05 aggregated real-rig row) must be **transcribed into `.planning/MANUSCRIPT-FINDINGS.md`
by the executor**, not referenced as a path — the file itself will not survive to be read later.
This research document does not transcribe findings itself (out of scope per the phase's
`Do NOT edit .planning/MANUSCRIPT-FINDINGS.md` fence); it flags the requirement for the plan.

### Wave 0 gaps

None identified. All six requirements have an existing test file or an existing runtime harness
(E1's CLI, E4's `--smoke`) to extend; no new test framework or fixture needs to be stood up
before implementation starts.

## Per-Requirement Notes

Only what CONTEXT.md does not already say.

- **FIX-01/FIX-02 (two-call-site pin):** see the D-02 probe finding above — `build_bounds` is
  imported independently at `interface_estimation.py:277` (stage-3 pass 1) and
  `refinement.py:184` (stage-3 pass 2, the intrinsic-refinement pass). Both run for E1's
  non-refractive arm because `_run_one_model` always calls with `refine_intrinsics=True`
  (`e1_refractive_comparison.py:312`). A plan that threads the pin to only one site will pass a
  first-pass-only check (optimality drop looks right) while still shipping a broken fix — the
  second pass's `water_z` column is where it actually surfaces.
- **`optimality_intrinsic` rising when `water_z` is pinned tight** is expected numerical
  behavior of a near-zero-width bound interval (see D-02 probe verdict above), not a regression
  signal. Worth noting in the plan's acceptance criteria so a reviewer doesn't mistake a larger
  optimality number for a worse solve — the acceptance metric stays the recovered `water_z`
  value (D-03), never this number.
- **FIX-05 second call site (D-09):** the verification vehicle table above names both
  `_run_check`'s `:1876` and `_run_full`'s `:1954` `build_grid_dataframe` calls
  explicitly because they are easy to fix one and miss the other.

## Open Questions (NONE)

None. D-02's probe resolved cleanly (no conditioning degradation), so the Claude's-Discretion
fallback item is moot and no user decision is required on that front. The remaining two
Claude's-Discretion items from CONTEXT.md (exact mechanism for reaching `build_bounds` from the
experiment layer; whether the `--check` exclusion list is E4-local or shared) are execution-time
choices for the planner/executor, not research gaps — this document does not resolve them because
they were explicitly left to discretion, not to research.
