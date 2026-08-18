# `experiments/` — paper experiment scripts

This directory holds the scripts that produce the SoftwareX manuscript's numbers and
figure inputs. It is **not part of the installed `aquacal` package**:
`pyproject.toml`'s `[tool.setuptools.packages.find]` scopes discovery to
`where = ["src"]`, so `experiments/` never ships in the wheel regardless of what lives
here. Each script is invoked directly as a module:

```bash
python -m experiments.e1_refractive_comparison
python -m experiments.e2_real_rig
python -m experiments.e7_interface_ablation
```

`experiments/` is linted (`ruff`) and covered by `pre-commit run --all-files` like the
rest of the repo, but it is **not pytest-collected** — its own logic is unit-tested
under `tests/unit/test_experiments_*.py` (schema, CLI parsing, the `--check` comparator),
and its measurement logic lives in `aquacal.datasets.pipelines` (the library computes;
the experiment orchestrates and writes files — P2/P3).

## 1. The uniform CLI contract

Every script in this directory shares one `argparse` parent
(`experiments._io.build_experiment_arg_parser`), giving each of them the identical five
flags:

| Flag | Default | Meaning |
|---|---|---|
| `--seed` | `42` | Random seed for scenario/detection generation. |
| `--out` | `experiments/results/` | Output directory for this experiment's artifacts. |
| `--force` | off | Overwrite existing per-configuration output files instead of skipping them. |
| `--smoke` | off | Run a fast, reduced-size variant that exercises the code paths without a full calibration — this is what CI's `experiments-smoke` job runs. |
| `--check` | off | Recompute fresh, compare against the committed baseline at a numeric tolerance, and print the worst offending cell. Never writes. |

`--check` and `--force` are **mutually exclusive** and this is enforced as a hard error
(`parser.error(...)`), not a silent preference for either flag — a script that quietly
picked one over the other would make it too easy to accidentally overwrite a committed
baseline while trying to verify it, or vice versa.

`--check` compares **numerically**, at a tolerance declared as a module constant in each
script (`CHECK_RTOL`, currently `1e-6` in every script), rather than byte-for-byte. A
strict byte compare across platforms fails on ordinary BLAS-level last-digit differences
in the nonlinear least-squares solver's exact convergence trajectory — and the
predictable consequence of a check that fails on harmless noise is that someone disables
the check entirely, which is precisely the determinism failure `--check` exists to catch.
Non-float columns still compare exactly; only float columns get the tolerance.
Determinism itself (sorted-key CSV writing, comparator correctness) is asserted
separately by unit tests, not by `--check` runs against a moving baseline.

## 2. The suite: one row per invocation

**One row per *invocation*, not per committed artifact.** An earlier version of this
section indexed the files under `experiments/results/` and listed a single bare command per
experiment — no `--seeds` row appeared anywhere in it, so an operator who followed it
produced the manuscript's single-seed numbers and **none of its seed bands**. Every
invocation the v2.1 re-run performs now has a row below, and each row's command is the one
`experiments/run_experiment_suite.sh` actually runs.

**Where the committed baselines live.** They are no longer under `experiments/results/`.
Plan 26-01 moved the whole pre-re-run tree aside to **`experiments/pre_rerun_baseline/`**
(preserving the sibling layout: `results/`, `results_e2_band/`, `results_e4_repeat/`,
`results_e6_repeat2/`, `results_e6_seed43/`, `results_linux32gb/`, plus `driver_state/`),
leaving `experiments/results/` empty for the re-run to write into. The archived tree is the
`--baseline-dir` every surviving `--check` path reads from, and it stays reachable for the
whole run — E2's control and E3's tier diff both compare against it. It is purged in Phase
30, against the **`pre-rerun-baseline`** tag, and not before.

**What the outputs should look like** is `experiments/EXPECTATIONS.md` — the written
hand-verification sheet, whose generated region is rendered from
`experiments/suite_expectations.json` and kept in step with it by a unit test. Read it
before judging a finished run; the `--check` contract it documents is not what it was
before Phases 23–25 moved four schemas.

### 2.1 The one driver

`experiments/run_experiment_suite.sh` is **the** entry point. It is the only suite driver on
disk; `rerun_19_3.sh`, `rerun_19_4.sh` and `rerun_19_5.sh` were superseded and archived under
`experiments/pre_rerun_baseline/driver_state/` once their stage functions had been lifted into
it. Launch it detached and unbuffered:

```bash
nohup bash experiments/run_experiment_suite.sh > experiments/suite_stdout.log 2>&1 &
disown
```

| Knob | Effect |
|---|---|
| `--profile smoke\|full` | `smoke` asserts artifact existence only; `full` asserts row counts as well. The frozen run is `full`. |
| `--skip-e2` | Skips the four E2 invocations — the only ones needing the 4.35 GB local frameset. |
| `--start-stage N` | Resume at stage `N` of the twenty. Completed stages are also skipped via the state file. |
| `--remaining-hours H` | Pre-flight warns when the manifest's estimate exceeds the window you declare. |
| `SUITE_WORKERS` | Concurrency width, default `4`, clamped to 4–5 (D-52). Never widen it on the probe's `recommended_workers: 16`, which was measured on E1 — the cheapest solve in the suite. |
| `SUITE_SERIAL=1` | Forces the fully serial path. The escape hatch if the pool is ever implicated in a result. |
| `SUITE_OUT_DIR`, `SUITE_BASELINE_DIR`, `SUITE_E2_RELEASE_CONFIG`, `SUITE_E2_INVOCATION_DIR` | Path overrides; Phase 27 repoints these for the Linux handoff. |

Two failure modes, deliberately different (D-01/D-03). A **pre-flight** failure — including
the `prelaunch_probe` legality check — **aborts** the run, because a bad environment
discovered at hour 18 is the expensive kind. A **completeness** failure at any later stage
sets a sticky non-zero exit and is logged loudly, but **never aborts the queue**: the
remaining stages still produce their artifacts, and the run's final exit code cannot lie
about the failure.

Serial wall clock over all twenty stages is **≈28.3–31.3 h** on the Windows box (20 logical
cores / 15.7 GiB); with the 4-wide pool, **≈15–17 h**. `e6_band` alone is ≈8.9 h — about 30%
of the serial total, and the critical path under any scheduling.

### 2.2 The twenty stages

Estimates and the concurrency attribute are the manifest's
(`experiments/suite_expectations.json`); `serial_alone` marks the four stages whose **timing
is itself the reported quantity**, which nothing may share the box with. Commands are given
in the driver's own variable form so a row can be diffed against the driver verbatim;
`${OUT_DIR}` is `experiments/results` unless `SUITE_OUT_DIR` says otherwise.

| # | Stage | Paper artifact | Exp. | Command | Output file(s) | Figure generator | Est. h | Conc. |
|---|---|---|---|---|---|---|---|---|
| 1 | `preflight` | — (run provenance) | — | `"${GATE_PYTHON}" -m experiments._run_manifest --out "${OUT_DIR}"` | `run_manifest.json` | — | 0.02 | conc. |
| 2 | `prelaunch_probe` | — (hard-abort gate) | — | inline heredoc calling `experiments.check_rerun_gates.legality_probe` over `${E6_BAND_SEEDS}` × `${PROBE_N_CAMERAS}` | — (verdicts to the log) | — | 0.01 | conc. |
| 3 | `e3` | Supplement solver constants, "converges in N steps", `tab:cpr` inputs, `\CPRParamsAside`/`\CPRReductionAside` | E3 | `python -u -m experiments.e3_derived_quantities --check --baseline-dir "${BASELINE_DIR}" --out "${OUT_DIR}"` **then** `python -u -m experiments.e3_derived_quantities --force --out "${OUT_DIR}"` | `code_constants.csv`, `newton_iterations.csv`, `cpr_grouping.csv`, `structural_scaling.csv`, `cpr_grouping.tex`, `cpr_derived_values.tex`, `e3_provenance.json` | the `.tex` fragments are their own generator | 0.005 | conc. |
| 4 | `fd_jacobian` | E-COV-02 / R1.2 Jacobian-accuracy statement | — | `python -u -m experiments.fd_jacobian_accuracy --out "${OUT_DIR}" --force` | `fd_jacobian_accuracy.csv`, `fd_jacobian_accuracy.json` | — (prose) | 0.05 | conc. |
| 5 | `e1` | §3 focal drift, RMS px, per-camera parameter errors; depth-generalization and XY-vs-Z curves | E1 | `python -u -m experiments.e1_refractive_comparison --force --out "${OUT_DIR}"` | `exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`, `exp3_xy_vs_z_anisotropy.csv`, `exp2_spatial_errors.csv` (gitignored, ~11 MB), `e1_benchmark_refractive.json`, `e1_benchmark_nonrefractive.json`, `e1_degeneracy_breakdown.json` | `DissertationFigures/.../aquacal/synthetic_validation.py` (a different repository) | 0.09 | conc. |
| 6 | `e7` | R4.2/R4.3 ablation table + trace panel, conditioning spectrum | E7 | `python -u -m experiments.e7_interface_ablation --force --out "${OUT_DIR}"` | `interface_ablation.csv` (48 rows = 4 arms × 12 cameras), `interface_ablation_conditioning.json`, four `e7_benchmark_*.json`, four `e7_trace_*.csv`, `e7_degeneracy_breakdown.json` | new figure module (Phase 19.2) | 0.09 | conc. |
| 7 | `e5` | R2 sensitivity panel (index-error band) | E5 | `python -u -m experiments.e5_index_sensitivity --force --out "${OUT_DIR}"` | `index_sensitivity.csv`, `e5_provenance.json`, `e5_degeneracy_breakdown.json` | `DissertationFigures/.../aquacal/` — downstream handoff (X5) | 0.76 | conc. |
| 8 | `e2_production` | §3 real-rig metrics; rig-3D figure inputs; reconstruction/reprojection distributions | E2 | `python -u -m experiments.e2_real_rig --config "${E2_PRODUCTION_CONFIG}" --out "${OUT_DIR}" --force` | `benchmark.json`, `real_rig_metrics.json`, `camera_parameters.csv`, `reconstruction_errors.csv`, `reprojection_residuals.csv`, plus the conditional `degenerate_observations.csv` / `all_observation_depths.csv` | `DissertationFigures/.../aquacal/zenodo_e2e.py` | 0.8–1.45 | conc. |
| 9 | `e6_repeat1` | R1.4 generalization table | E6 | `rm -rf "${OUT_DIR}/e6_configs"` + `rm -f generalization_sweep.csv e6_provenance.json`, **then** `python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR}"` | `generalization_sweep.csv` (14 rows), `generalization_sweep_per_camera.csv`, `e6_provenance.json`, `e6_configs/*.json` | `DissertationFigures/.../aquacal/` — downstream handoff (X5) | 2.78 | conc. |
| 10 | `reconstruction_bootstrap` | COV-08 bootstrap CI band over reconstruction error | — | `python -u -m experiments.reconstruction_bootstrap --out "${OUT_DIR}" --force` | `reconstruction_bootstrap.json` | — (prose / CI band) | 0.06 | conc. |
| 11 | `e2_timing` | §3 real-rig **wall clock** | E2 | `python -u -m experiments.e2_real_rig --config "${E2_TIMING_CONFIG}" --out "${OUT_DIR_E2_TIMING}" --force` | `experiments/results_e2_timing/benchmark.json` | — (prose) | 0.8–1.45 | **serial_alone** |
| 12 | `e2_memory` | §3 real-rig **peak RSS** | E2 | `python -u -m experiments.e2_real_rig --config "${E2_MEMORY_CONFIG}" --out "${OUT_DIR_E2_MEMORY}" --force` | `experiments/results_e2_memory/benchmark.json` | — (prose) | 0.8–1.45 | **serial_alone** |
| 13 | `e7_band` | MF-05's per-arm seed bands — the milestone's only surviving accuracy claim | E7 | `python -u -m experiments.e7_interface_ablation --seeds "${BAND_SEEDS}" --out "${OUT_DIR}"` | `interface_ablation_band.csv` (480 rows), `e7_seed_band_provenance.json`, `e7_seed_band_degeneracy_breakdown.json` | new figure module | 1.0–2.0 | conc. |
| 14 | `e5_band` | E5's seed band | E5 | `python -u -m experiments.e5_index_sensitivity --seeds "${E5_BAND_SEEDS}" --out "${OUT_DIR}" --force` | `index_sensitivity_seed_band.csv` (66 rows), `e5_seed_band_provenance.json`, `e5_seed_band_degeneracy_breakdown.json` | downstream handoff (X5) | 2.34 | conc. |
| 15 | `e2_band` | E2's real-rig seed band (three seeds, sequential full calibrations) | E2 | `python -u -m experiments.e2_real_rig --emit-band-configs --config "${E2_RELEASE_CONFIG}" --band-seeds "${E2_BAND_SEEDS}" --band-dir "${OUT_DIR_E2_BAND}"`, **then per seed** `--config "${OUT_DIR_E2_BAND}/config_seed${seed}.yaml" --out "${OUT_DIR_E2_BAND}/seed_${seed}_e2_out" --force` | `experiments/results_e2_band/e2_band_scope.json` + one output tree per seed | — (prose) | 2.42 | conc. |
| 16 | `e1_band` | E1's **noise-axis** band (BAND-01 / MF-22) | E1 | `python -u -m experiments.e1_refractive_comparison --seeds "${E1_BAND_SEEDS}" --out "${OUT_DIR}"` | `exp1_band.csv` (256 rows), `exp1_parameter_band.csv` (384 rows), `e1_seed_band_provenance.json`, `e1_seed_band_degeneracy_breakdown.json` | `synthetic_validation.py` (a different repository) | 2.8 | conc. |
| 17 | `e4` | Main-text runtime table + supplement cameras×frames grid | E4 | `python -u -m experiments.e4_benchmark_grid --force --out "${OUT_DIR}"` | `benchmark_grid.csv` (10 rows), `benchmark_grid.tex`, `e4_cells/*/benchmark.json` | new figure module (Phase 19.2) | 3.57 | **serial_alone** |
| 18 | `e6_band` | E6's frozen seed band | E6 | `python -u -m experiments.e6_generalization_sweep --seeds "${E6_BAND_SEEDS}" --axes index,layout,cameras --out "${OUT_DIR}" --force` | `generalization_sweep_band.csv` (84 rows), `generalization_sweep_per_camera_band.csv`, `e6_seed_band_provenance.json` | downstream handoff (X5) | 8.9 | conc. |
| 19 | `e7_focal_standoff` | COV-08 focal-drift/standoff pairing (E7 half) | E7 | `python -u -m experiments.e7_focal_standoff_analysis --out "${OUT_DIR}"` | `e7_focal_standoff.csv` (4 rows) | — (analysis output) | 0.02 | conc. |
| 20 | `e4_repeat` | COV-06 run-to-run wall-clock spread (`seconds_total_spread_pct`) | E4 | for `repeat` in 1 2, for `cell` in `8x100 12x100 16x100`: `python -u -m experiments.e4_benchmark_grid --cell "${cell}" --out "${OUT_DIR_E4_REPEAT}" --force`; then `--splice-repeat "${OUT_DIR_E4_REPEAT}" --out "${OUT_DIR}"` | `benchmark_grid_repeat.csv` (6 rows) | — (prose) | 0.99 | **serial_alone** |

Seed lists, from the driver: `BAND_SEEDS=42..51` (ten), `E6_BAND_SEEDS`/`E5_BAND_SEEDS=42..47`
(six), `E1_BAND_SEEDS=42,43,44,45` (four), `E2_BAND_SEEDS=42,43,44` (three).

Three notes the table cannot carry:

- **E1's band is a UNIFORM grid.** `_run_band` is a strict cartesian product of the requested
  seeds with `NOISE_LEVELS` (`[0.25, 0.5, 0.82, 1.2]`), so `--seeds` alone produces the whole
  grid and no new flag is needed. Four seeds × four levels × 16 rows per cell = 256 rows of
  `exp1_band.csv`, × 24 = 384 rows of `exp1_parameter_band.csv`. It cannot express a ragged
  grid, and two invocations would overwrite rather than compose. 0.5 px is one of the four
  levels, which matters: the headline ratio band and every ledger number backed by
  `exp1_band.csv` live there.
- **E6's band drops the scale axis** (`--axes index,layout,cameras`): 14 configurations × 6
  seeds = **84 rows**. The scale axis appears in zero rows of the manuscript's numbers, and
  this is the suite's dominant stage, so the cut is where the hours are.
- **`e6_repeat2` is not a stage.** The paired determinism sweep was a Phase 19.3 deliverable,
  costs ~1.8–2.8 h, and produces a response-letter statistic nothing in §3 cites. It is OFF
  under **both** profiles.

### 2.3 E2 runs as four distinct invocations, and the split is not tidiness

E2 appears four times above because one run cannot honestly produce all four results.
`--emit-invocation-configs` derives three configs from the release config into
`${E2_INVOCATION_DIR}` (default `experiments/results_e2_invocations`):

| Config | Stage | Distinguishing key | Why it must be its own run |
|---|---|---|---|
| `config_e2_classification.yaml` | `e2_production` | `internals.log_all_observation_depths: true` | The instrumentation is a **YAML key, not a CLI flag**, which is the whole reason a generated config exists rather than an extra argument. |
| `config_e2_timing.yaml` | `e2_timing` | neither instrumentation key; `benchmark_memory: false` | Memory instrumentation costs 2.7–5.5% wall clock. A run reporting both a timing and a peak-RSS number reports a timing inflated by the measurement of the other. |
| `config_e2_memory.yaml` | `e2_memory` | `internals.benchmark_memory: true` | Same reason, from the other side. |

The fourth invocation is `e2_band`, which emits its own per-seed configs into
`experiments/results_e2_band/` and runs each seed's calibration sequentially (48–87 min
each). It writes into an in-repo **sibling** of `${OUT_DIR}`, never into it and never into or
under the release tree, so a `--check` or gate run against `${OUT_DIR}` can never confuse band
output with the production run's own artifacts. `check_e2_band` resolves it as
`${OUT_DIR}.parent / "results_e2_band"`; keep it a sibling.

Both `e2_timing` and `e2_memory` are `serial_alone`. A peak-RSS number measured while another
calibration held 3.5 GiB is a measurement of the queue, not of the algorithm.

### 2.4 Five ordering constraints, and why they are edges rather than comments

The stage order is a topological sort of the manifest's `depends_on` edges, shortest-first
within each dependency level, so a systematic failure surfaces in seconds rather than after
the longest stage. Five of those edges are correctness, not preference:

1. **`e4` after `e2_production`.** `resolve_e2_benchmark_path` (`e4_benchmark_grid.py:261`,
   with the `__file__`-anchored `E2_BENCHMARK_PATH` constant at `:256`) looks for E2's
   `benchmark.json`; when it is absent the resolver returns `None`, E4 quietly **drops the
   real-rig row**, and `benchmark_grid.csv` comes back with **9 rows instead of 10**. Nothing
   fails and nothing warns loudly, and the missing row is the only one tying the synthetic
   grid to the real rig. *(This corrects an earlier statement here that E4 "reads the real-rig
   record from a hardcoded `E2_BENCHMARK_PATH` that does not follow `--out`". FIX-05 in Phase
   23 replaced the bare constant with the resolver; the old line reference was also stale.)*
2. **`e7_focal_standoff` after `e7_band`.** It reads the hardcoded, cwd-relative
   `Path("experiments/results") / "interface_ablation_band.csv"` — deliberately never the
   `--out` directory — so the band must have landed first. Out of order it gives a
   missing-file error, not a wrong number.
3. **`reconstruction_bootstrap` after `e2_production`.** It reads
   `experiments/results/reconstruction_errors.csv` and the hardcoded
   `REAL_RIG_METRICS_PATH = Path("experiments/results/real_rig_metrics.json")`.
4. **`e6_repeat1` and `e6_band` may never overlap.** Both write E6 artifacts under the shared
   `${OUT_DIR}`, and E6's checkpoint cache is seed-blind.
5. **E3's `--check` strictly before its `--force`.** The `--check` is one of only two
   `--check` paths that is still a real reproduction signal, and `--force` rewrites the tier
   CSVs it would otherwise be checked against. `--baseline-dir` goes on `--check` only — E3's
   parser rejects it with `--force`, because it names the directory `--check` reads baselines
   *from*.

`e4_repeat` runs **both** repeats of each cell back-to-back inside one stage. COV-06's
deliverable is run-to-run wall-clock spread; if the two repeats of a cell met different memory
pressure because something else ran between them, the "spread" would measure paging rather
than the algorithm — a decomposition of pure noise, this project's most recurrent error.

### 2.5 Provenance: three record shapes, no fourth

Every artifact below has a genuine four-field provenance record behind it — seed, AquaCal
version, git SHA, and the Python/NumPy/SciPy/OS environment — in one of exactly three shapes:

- A `benchmark.json`-shaped record (`schema_version: 1`, a `stages` block): either the genuine
  pipeline-written record (E2, via `run_calibration_from_config`) or a direct-call record
  assembled from the same pure `aquacal.io.assemble_benchmark_record` (E1, E7, E4's per-cell
  records — these call `calibrate_synthetic` directly and never touch the pipeline's
  config-driven entry point).
- A minimal, `stages`-free sidecar for the experiments that never run a calibration or have no
  per-row record: `e3_provenance.json`, `e5_provenance.json`, `e6_provenance.json`, and the
  band sidecars `e1_seed_band_provenance.json`, `e5_seed_band_provenance.json`,
  `e6_seed_band_provenance.json`, `e7_seed_band_provenance.json`.
- E6's per-configuration `e6_configs/*.json` checkpoints, which carry the same fields
  individually and double as resumability checkpoints.

`tests/unit/test_experiments_provenance.py`'s `CSV_TO_RECORD` names the covering record for
every committed CSV, and a CSV committed without an entry there fails CI. No experiment
invents a fourth shape.

### The accuracy tree and the timing tree are deliberately different trees

`experiments/results/` holds the **accuracy** numbers, measured on Windows.
`experiments/pre_rerun_baseline/results_linux32gb/` holds the pre-re-run **timing and memory**
numbers, measured on 32 GB Linux, because the accuracy machine has 16 GB and a 13-camera run
peaks at 10.26 GiB there. It is a sibling distinguished by **machine**, not by experiment
variant — so its rows are not interchangeable with the accuracy tree's and must not be diffed
against them as if they were repeats. `results_linux32gb/linux32gb_scope.json` is that tree's
scope and confound-control statement: read it before citing anything from there. It also
carries the E2 OpenCV 4.13-vs-4.14 control behind MF-20, which is why the OpenCV version is
named throughout §3 below.

One consequence, still visible in that archived tree: its `benchmark_grid.csv` carries the
**nine synthetic cells only**, with no real-rig row. That is ordering constraint 1 above,
before FIX-05 named it — the row was dropped and folded back in by hand.

The v2.1 re-run's own timing numbers come from the `e2_timing`, `e2_memory`, `e4` and
`e4_repeat` stages, which is what `serial_alone` exists to protect.

> ### ⚠ Three `generalization_sweep.csv` rows did not converge — read before citing E6
>
> Since plan 19.2-27, E6 records `optimality_stage3_interface_optimization` and
> `optimality_stage3_intrinsic_pass` per configuration. On the first run carrying them
> (`19.2-28-SUMMARY.md`), **three of fourteen rows came back 3–4 orders of magnitude above the other
> eleven — and all three are published under `status="ok"` with a plausible reprojection RMS**:
> `index=1.42` (optimality 51.9), `scale=half_scale` (27.3 / 140.3), and `layout=ring` (4.20 on the
> intrinsic pass), against 0.0016–0.117 for the rest.
>
> **Accuracy appears unaffected** — reconstruction RMSE is indistinguishable between the flagged and
> healthy groups, and the worst reconstruction in the table belongs to a *healthy* configuration.
> The diagnosed cause is that board corners protrude through the water surface (61/8800 = 0.69% of
> corners), so those observations leave the refractive model's domain and are continued with a
> pinhole extension whose derivative discontinuity inflates a max-norm gradient. Phase 19.3 fixed
> the geometry and the family was re-measured; the note is retained because the *reading rule* it
> states outlives the defect.
>
> **Consequences for anyone using this table.** Do not quote those rows as converged results
> without stating their optimality — see **MF-07** in `.planning/MANUSCRIPT-FINDINGS.md`, where the
> decision is recorded as OPEN. And never quote optimality to more than one significant figure: it
> varies ~2x between runs of identical code, so it supports an order-of-magnitude reading and
> nothing finer.

`e4_benchmark_grid.py` is a **direct-call synthetic benchmark grid** (D-03/D-26): it
builds `generate_camera_array` + `generate_board_trajectory` scenes and calibrates them via
the same direct-call path E1/E7 use, rather than subsampling a real 13-camera YAML through
the pipeline's config-driven entry point. A real 13-camera rig run already takes 48-87
minutes (`CLAUDE.md`) and cannot reach 16 cameras (unreachable from a 13-camera rig), so a
real cameras-x-frames sweep was out of scope.

Two columns exist specifically so a reader cannot compare the nine synthetic rows against
E2's real-rig row as if they measured the same thing: `timing_scope` is `optimization_only`
for the nine synthetic cells (Stage 3 wall-clock only) and `end_to_end` for the real-rig row
(includes detection loading, auxiliary registration, and validation); `record_source` is
`assembled` (built from a per-cell `benchmark.json` by this script) for the synthetic cells
and `pipeline` (written directly by `run_calibration_from_config`) for the real-rig row.
`benchmark_grid.tex` renders the real-rig row in its own labeled block, never as a tenth
point on the nine-cell scaling curve.

`python -m experiments.e4_benchmark_grid --check` re-aggregates the per-cell
`benchmark.json` files under `e4_cells/` and compares the result against the committed
`benchmark_grid.csv` — it never re-runs a cell, and is not evidence the nine calibrations
themselves reproduce, only that the aggregation and the committed CSV agree with the on-disk
per-cell records. Because `_run_check` never re-runs a cell, its freshly-built frame always
reports `exit_code=None` while the committed CSV carries the real per-run exit codes, so E4's
`--check` is **structurally always-red on `exit_code` and `status_reason`** while all 33
metric columns reproduce to 1e-6. Those two columns are named — not heuristically
detected — in `CHECK_EXCLUDED_COLUMNS` (`e4_benchmark_grid.py:215`); see
`experiments/EXPECTATIONS.md` for the full `--check` contract across this re-base.

### DATA-01b — three E2 artifacts live in the Zenodo archive, not in this repo

`calibration.json`, `reprojection_residuals.csv` and `reconstruction_errors.csv` were removed
from version control once the Zenodo `real-rig` archive was published, so that the repo-wide
1000 KB `check-added-large-files` guard could be restored with no exclusion. They ship inside
the archive under `reference_outputs/`.

| Artifact | Where to get it now |
|---|---|
| `reconstruction_errors.csv` | Archive `reference_outputs/` — **byte-identical** to the removed copy |
| `reprojection_residuals.csv` | Archive `reference_outputs/` — **byte-identical** to the removed copy |
| `calibration.json` | Archive `reference_outputs/` — **equivalent, not identical** (see below) |

```python
from aquacal.datasets import load_example
ref = load_example("real-rig").cache_path / "reference_outputs"
```

Or regenerate them locally with the `e2_production` invocation above, which takes ~50 minutes.

**This is also why E2's `--check` is weaker than it looks.** Two of the three artifacts E2
compares have no committed baseline at all, so `--check` reports **N/A** for them rather than
a pass. Do not read "`--check` survives on E3 and E2" as three surviving comparisons for E2;
it is one (`camera_parameters.csv`), and the better-anchored E2 control is `check_e2_band`'s
numeric comparison of `real_rig_metrics.json` at `_E2_METRICS_RTOL = 1e-6`
(`check_rerun_gates.py:1378`). `experiments/EXPECTATIONS.md` states this in full.

**The `calibration.json` caveat.** The archive ships the **2026-08-10 image-source** run, while
the file removed from this repo was the **2026-07-31 video-source** run. Both are library
`1.8.0` and they agree to ~1.5e-8 on `water_z` — the floating-point floor, and the same
equivalence MF-19's control established when it held the library fixed and varied only the frame
source. For any purpose short of byte-comparison the archive copy is the same artifact. If you
need those exact bytes, take them from git history at `25655f7`, not from the archive.

`reconstruction_bootstrap.py` resolves its input automatically: an explicit
`--reconstruction-errors` path, else a local `experiments/results/` copy, else the published
archive. It never downloads at import time.

### Which committed artifacts are pre- and which are post-D-27

D-27 (plan 19.2-18) changed `generate_board_trajectory`'s sampling volume to center on the
camera array's centroid rather than the origin — a deliberate, **non-inert** change for the
grid family (E4, E6), which calls `generate_board_trajectory` directly through
`build_grid_scenario`. It never fires for the "realistic" family (E1, E2, E3, E5, E7), which
builds its scenes through `generate_real_rig_trajectory` or the real video frameset instead —
a structurally different code path that D-27 never touches.

- **Structurally unaffected, and proven so mechanically, not asserted:** E1, E2, E3, E5, E7.
  Plan 19.2-18 backs this with three independent proofs — two frozen-anchor exact-equality
  tests (`generate_real_rig_trajectory` and `create_scenario("realistic")` bit-identical
  pre/post D-27), a source-scanning grep-gate (no realistic-path caller ever passes an
  explicit `center` override), and four passing `--check` reproductions (E1, E3, E5, E7)
  against the then-committed baselines, all recorded in `19.2-18-SUMMARY.md` § Task 3. E2
  never runs a synthetic scenario generator at all.
- **Regenerated after D-27, on the redesigned geometry:** E4 (`19.2-21-SUMMARY.md`) and E6
  (`19.2-22-SUMMARY.md`). Both artifacts postdate D-27 by construction — there is no pre-D-27
  baseline for either, because D-27 is bundled with D-28/D-29's geometry rescale in the same
  commits (`d5d9dde`, `a2b244d`) those runs are built on.

All of the above describes the **archived** tree under `experiments/pre_rerun_baseline/`. The
v2.1 re-run regenerates the whole family at one frozen sha, which is the point of running it.

### `cpr_grouping.tex` is generated but never `\input`; `tab:cpr` is hand-transcribed

**Correcting an earlier claim in this file — that `cpr_grouping.csv` is the only thing
`tab:cpr` is built from.** Verified against the live manuscript on 2026-08-18: `tab:cpr` lives at
`supplement.tex:449` with **six rows, all shared-interface**, and the generated
`cpr_grouping.tex` fragment is **not `\input` anywhere**. The table is **hand-transcribed**.
The generated fragment is therefore currently decorative — it is produced on every E3 run and
read by nothing.

Two consequences:

- **`--include-per-camera-latex` stays OFF.** The flag renders `shared_interface=False` rows
  into `cpr_grouping.tex`. Turning it on would enlarge a fragment nothing reads and invite a
  reader to believe it is the source of a table it does not feed.
- The derivation, and its interaction with Phase 27's pre-freeze gate that every §3-facing
  number has a generating emitter, are recorded as **MF-23** in
  `.planning/MANUSCRIPT-FINDINGS.md`. That entry and this section must agree; whether to wire
  the fragment in or drop it is the manuscript session's call, not this repo's.

What remains true about the CSV: every `cpr_grouping.csv` row is a tilt-enabled
(`normal_fixed=False`) configuration, matching `CalibrationConfig.interface_normal_fixed`'s
default and E2's real-rig run. Exactly one row (the shared-interface 13-camera/200-frame
tilt+intrinsics row) is copied verbatim from E2's `benchmark.json`; the rest are computed by
`experiments.e3_derived_quantities` directly against the library's own
`build_jacobian_sparsity`/`build_structural_column_groups`. An earlier design split `tab:cpr`
across this file and E4's per-cell grid CSV; that split was withdrawn (review H1) because E4's
cells run at a real, sparser scene rather than the idealized full-visibility fixture
`tab:cpr`'s numbers describe. **`benchmark_grid.csv` also carries
`n_params`/`n_groups`/`fd_reduction` columns, but they describe E4's own runs and feed no
published table.** The `normal_fixed`/`shared_interface` columns present in both files are what
let a reader tell a `cpr_grouping.csv` row from a `benchmark_grid.csv` cell apart.

### Every cell in E4 and E6 runs tilt-enabled

E4's nine cells and E6's sweep both run at `normal_fixed=False`
(`experiments.e4_benchmark_grid.GRID_NORMAL_FIXED`, imported by E6 rather than restated),
matching `CalibrationConfig.interface_normal_fixed`'s default and E2's real-rig run. This is
why every synthetic-grid CSV in this directory carries a `normal_fixed` column — a reader
comparing a row here against a differently-configured run elsewhere can check it rather than
assume it.

### The seed carve-out

E1's and E7's Phase-19.1 records (`e1_benchmark_refractive.json`,
`e1_benchmark_nonrefractive.json`, and E7's four `e7_benchmark_*.json` arms) predate
`solver_config["seed"]`, which plan 19.2-02 added to the direct-call write path after these
six records were already committed. `tests/unit/test_experiments_provenance.py`'s
`SEEDLESS_LEGACY_RECORDS` set exempts exactly these six files from the otherwise-universal
"every committed record carries a seed" check, and a companion test fails the moment any of
the six is regenerated with a seed — at which point the exemption must be removed by hand.
**The v2.1 re-run regenerates all six** (stages 5 and 6 above), so expect that companion test
to fire and the exemption to be retired as part of the re-baseline.

### The scripts with no row of their own

Every runnable script in this directory is now invoked by the driver except one. Three that
used to be orphans — never invoked by any driver, which is why their artifacts were absent
from the committed tree while the manuscript rested on them — are stages 4, 10 and 19 above.

| Script | What it is | Tests | Suite stage |
|---|---|---|---|
| `e7_focal_standoff_analysis.py` | Pure re-analysis of `interface_ablation_band.csv` for the focal-drift/standoff pairing (COV-08, E7 half). Never regenerates its input; ignores `--smoke` entirely, so its artifact is a `full`-profile expectation only. | `tests/unit/test_e7_focal_standoff.py` | 19 (`e7_focal_standoff`) |
| `reconstruction_bootstrap.py` | Frame-clustered bootstrap CI over `reconstruction_errors.csv`. The resampling unit is the frame, not the row. Performs no calibration. | `tests/unit/test_reconstruction_bootstrap.py` | 10 (`reconstruction_bootstrap`) |
| `fd_jacobian_accuracy.py` | Compares the shipped 2-point finite-difference Jacobian against a Richardson reference (E-COV-02 / R1.2) without deriving the analytic Jacobian. | — none — | 4 (`fd_jacobian`) |
| `check_rerun_gates.py` | Machine-checkable post-run gates over an output directory's existing artifacts, plus the completeness gate reading `suite_expectations.json`. Reports PASS/FAIL/N/A and exits non-zero on any FAIL. Runs nothing and regenerates nothing. | `tests/unit/test_rerun_gates.py`, `tests/unit/test_expectations.py` | — (a verification tool, invoked by the driver after each stage and once at the end) |
| `_run_manifest.py` | Emits the one-shot `run_manifest.json` at pre-flight. | `tests/unit/test_run_manifest.py` | 1 (`preflight`) |
| `render_expectation_sheet.py` | Regenerates `EXPECTATIONS.md`'s generated region from `suite_expectations.json`. Not part of the run. | `tests/unit/test_expectations.py` | — |

The helper shell scripts (`prelaunch_gate.sh`, `seed_sweep_19_3.sh`, `e6_legal_seed_probe.sh`)
are not suite stages either; `prelaunch_gate.sh`'s `ENV_VERSION_MATCH` check is the one §7
below tells you to run before launching.

The experiment scripts all inherit the same five-flag CLI contract described in §1.

## 3. E2 has two invocation paths — read this before citing a number

`python -m experiments.e2_real_rig` (no `--config`) runs against the **published Zenodo
archive**. This is the path a reader without the raw videos follows, and it is the
default so that path stays available. It currently reproduces a **1,817-comparison**
run (60 usable frames -> 12 validation frames), not the manuscript's §3 numbers.

`python -m experiments.e2_real_rig --config <release config>` runs the **full frameset**
from local raw videos (`Desktop\Aqua\AquaCal\raw_videos\`) using the same
`detection.frame_step: 30` / `optimization.max_calibration_frames: 200` /
`validation.holdout_fraction: 0.2` settings as the release calibration, and reproduces §3
**exactly** — all nine named quantities at 0.000% delta, 7,762 comparisons (see
`19.1-E2-DELTA-TABLE.md`).

**Both paths' reference numbers were produced under OpenCV 4.13.0** — name that version
before citing either. The real-rig numbers move with the OpenCV version, not just the
AquaCal version: `detection.py:64` constructs `cv2.aruco.CharucoDetector` directly, so the
corner set is entirely OpenCV's, and a single-variable control (2026-08-12, same machine,
cloned env differing *only* in OpenCV) reproduced this repo's committed numbers to <=4.7e-09
relative under 4.13.0 while 4.14.0 detected 450 fewer corners and moved `reconstruction.rmse`
by +7.8%. Nothing measured says which version detected the *right* set — neither is "more
correct" — so the environment is named rather than the numbers changed. Holding OpenCV fixed,
the aquacal 1.8.0 -> 2.0.1 gap and the Windows -> Linux platform change are both inert on
real data (MF-20). Every `benchmark.json` records `opencv_version` in its `environment` block.

**The published Zenodo archive currently ships only the smaller, 60-frame extraction.**
A reader following the default (no-`--config`) path today reproduces the
1,817-comparison numbers, not §3's. Closing that gap — regenerating the published
archive to the full frameset — is tracked as **DATA-01a** in Phase 21 and is a
prerequisite for publication, not a nice-to-have (`19.1-E2-FRAMESET-PROVENANCE.md`).
The committed CSVs in `experiments/results/` come from the full-frameset local-video run,
which the published archive cannot currently reproduce; that gap closes when Phase 21's
DATA-01/02/03 lands.

## 4. The gauge-freedom correction

A per-camera Z position error is only meaningful up to the world frame's Z datum, which
the reference camera (`cam0`) pins at zero by construction — it sits at the world-frame
origin, `p_cam = R @ p_world + t`. Without correction, a global datum offset that the
optimizer applied to the entire rig (an artifact of *where* "Z=0" is chosen, not a real
geometric error) gets charged entirely to the non-reference cameras while the reference
camera's own near-zero raw error is left uncorrected, confounding any cross-camera Z-error
comparison.

`aquacal.datasets.pipelines.compute_per_camera_errors(..., gauge_correct_z=True)` (E1
passes `True`; the default is `False` so no existing caller's behavior changes) subtracts
the mean raw Z error of the non-reference ("free") cameras from **every** camera's Z
error, including the reference camera's own. This is why a reference camera's row reads:

- `xy_position_error_mm == 0.0` — the reference camera is pinned at the world origin, a
  separate, purely geometric fact with zero optimizable freedom, unrelated to the Z
  correction.
- `z_position_error_mm` after correction is a **small nonzero residual**, not `0.0` — the
  correction reveals the systematic Z shift the model applied to the whole rig, which is
  a real (if small) quantity, not an artifact of the reference camera's fixed position.

## 5. What "fixed intrinsics" means in E7

E7's two fixed-intrinsics arms hold camera intrinsics at `scenario.intrinsics` — ground
truth (`intrinsics_source = ground_truth_fixed` in the emitted CSV) — not at an
independently-estimated in-air Stage-1 calibration. This is deliberate, not a shortcut:
E7's primary result is a **geometric degeneracy** in the extrinsics/interface
parameterization, which exists regardless of intrinsic accuracy. Perturbing the
intrinsics would inject a second, unrelated error source (focal error propagating into
recovered height) into an arm whose whole purpose is isolating the first one. Because the
intrinsics are exact, no focal error can propagate into the recovered heights — this
makes the fixed-intrinsics, per-camera arm the **strongest possible case** for per-camera
mode, and a degeneracy demonstrated under best-case conditions is the stronger claim,
because noise cannot be blamed for it.

## 6. How to read E7's output

The failure E7 demonstrates is a **height/distance** degeneracy
(`C_z_i` against `water_z_i` — the per-camera height and per-camera interface distance),
**never** a focal-length or standoff-distance failure. Naive per-camera mode packs `N`
free `water_z_i` parameters beside `N` free camera centers `C_z_i`; only the *sum*
(`camera_height + water_z`, the absolute surface height) is physically meaningful and
must be common to all cameras, because every camera in the rig looks through the same
flat surface — but nothing in that parameterization enforces it, and a fixed sum with
compensating errors in each addend fits the 2D observations equally well.

`reprojection_rms_px_control` is a recorded **control**, not evidence: a height/distance
degeneracy is a flat cost valley, so RMSE stays low in both the shared and per-camera
arms even though the per-camera arm's recovered heights scatter by more than a
centimeter across cameras that physically share one water surface. If RMSE had also
degraded sharply in the per-camera arm, the flat-valley framing would need
re-examining — the column is explicitly suffixed `_control` rather than presented as if
it were the finding.

The refine-intrinsics-ON arms are **AquaCal's own design rationale for importing
Stage-1 in-air intrinsics** rather than re-deriving them jointly with everything else —
they are **not** "what CalibMar produces." CalibMar solves each camera independently in
its own local frame and has no such redundancy; it works correctly in its intended
regime. The refine-ON arms here measure a design choice AquaCal made for its own
architecture, not a competing tool's behavior.

## 7. Reproducing a number

**Precondition — a source checkout must carry a *current* editable install.** Run
`pip install -e . --no-deps` in the environment you are about to use, and re-run it after
**any** change to `pyproject.toml`'s `version`. `aquacal.__version__` and the
`environment.aquacal_version` field written into every record both resolve through
`importlib.metadata.version("aquacal")` — i.e. *installed distribution metadata*, which an
editable install writes once and never refreshes. The `.pth` still resolves imports to the
working tree, so between a version bump and the next reinstall the code that runs is the new
tree while every artifact it produces is stamped with the old version. Nothing fails loudly;
you simply get a confident, plausible, wrong provenance record. `experiments/prelaunch_gate.sh`'s
`ENV_VERSION_MATCH` check asserts this before a queue launches, and `benchmark.json`'s
`environment.aquacal_version_declared` records the declared version beside the installed one so
an escaped case is visible after the fact.

### 7.1 Reproducing the whole suite

Do not assemble the run by hand from the commands below. Every invocation, in dependency
order, with the pre-flight refusals, the completeness gate and the concurrency pool, is:

```bash
bash experiments/prelaunch_gate.sh              # ENV_VERSION_MATCH and friends, first
nohup bash experiments/run_experiment_suite.sh --profile full \
  > experiments/suite_stdout.log 2>&1 &
disown
```

Expect **≈15–17 h** with the default 4-wide pool, **≈28–31 h** serial. Resume a died run with
`--start-stage N`; completed stages are skipped from the state file regardless. `--skip-e2`
drops the four E2 invocations, which are the only ones needing the local frameset. Judge the
finished tree against `experiments/EXPECTATIONS.md`, not against a memory of what the old
tree looked like — four schemas moved in Phases 23–25.

### 7.2 Reproducing one number

Every command in this block is one the driver runs, copied from §2.2 and split by experiment.
`${OUT_DIR}` is `experiments/results`, `${BASELINE_DIR}` is
`experiments/pre_rerun_baseline/results`, and `${E2_INVOCATION_DIR}` is
`experiments/results_e2_invocations`. **Where a band is listed, the band is the paper's
number** — the single-seed run beside it is not a substitute for it.

```bash
# --- E1: synthetic refractive-vs-non-refractive comparison -------------------
python -u -m experiments.e1_refractive_comparison --force --out "${OUT_DIR}"   # single seed, ~5 min
python -u -m experiments.e1_refractive_comparison \
    --seeds 42,43,44,45 --out "${OUT_DIR}"                                     # THE NOISE BAND, ~2.8 h
#   4 seeds x 4 noise levels {0.25, 0.5, 0.82, 1.2} px, uniform: 256 rows of
#   exp1_band.csv and 384 of exp1_parameter_band.csv. The headline ratio band
#   lives at 0.5 px, which is one of the four levels.

# --- E2: real rig, FOUR distinct invocations (see 2.3) -----------------------
python -u -m experiments.e2_real_rig --emit-invocation-configs \
    --config <path/to/release/config.yaml> --invocation-dir "${E2_INVOCATION_DIR}"
python -u -m experiments.e2_real_rig \
    --config "${E2_INVOCATION_DIR}/config_e2_classification.yaml" --out "${OUT_DIR}" --force
python -u -m experiments.e2_real_rig \
    --config "${E2_INVOCATION_DIR}/config_e2_timing.yaml" --out experiments/results_e2_timing --force
python -u -m experiments.e2_real_rig \
    --config "${E2_INVOCATION_DIR}/config_e2_memory.yaml" --out experiments/results_e2_memory --force
python -u -m experiments.e2_real_rig --emit-band-configs \
    --config <path/to/release/config.yaml> --band-seeds 42,43,44 \
    --band-dir experiments/results_e2_band
python -u -m experiments.e2_real_rig \
    --config experiments/results_e2_band/config_seed42.yaml \
    --out experiments/results_e2_band/seed_42_e2_out --force                   # ...and once per band seed
#   Never run the timing and memory invocations concurrently with anything:
#   the number each produces IS the measurement.

# --- E3: derived quantities and code constants (~10 s) -----------------------
python -u -m experiments.e3_derived_quantities --check --baseline-dir "${BASELINE_DIR}" --out "${OUT_DIR}"
python -u -m experiments.e3_derived_quantities --force --out "${OUT_DIR}"      # --check FIRST, always
#   --baseline-dir goes on --check only; the parser rejects it with --force.

# --- E4: cameras x frames synthetic benchmark grid ---------------------------
python -u -m experiments.e4_benchmark_grid --force --out "${OUT_DIR}"          # ~3.6 h; run AFTER E2
for repeat in 1 2; do for cell in 8x100 12x100 16x100; do \
  python -u -m experiments.e4_benchmark_grid --cell "${cell}" --out experiments/results_e4_repeat --force; \
done; done
python -u -m experiments.e4_benchmark_grid --splice-repeat experiments/results_e4_repeat --out "${OUT_DIR}"

# --- E5: refractive-index sensitivity ----------------------------------------
python -u -m experiments.e5_index_sensitivity --force --out "${OUT_DIR}"       # single seed
python -u -m experiments.e5_index_sensitivity \
    --seeds 42,43,44,45,46,47 --out "${OUT_DIR}" --force                       # THE BAND, ~2.3 h, 66 rows

# --- E6: generalization sweep ------------------------------------------------
python -u -m experiments.e6_generalization_sweep --force --out "${OUT_DIR}"    # ~2.8 h, 14 rows
python -u -m experiments.e6_generalization_sweep \
    --seeds 42,43,44,45,46,47 --axes index,layout,cameras --out "${OUT_DIR}" --force
#   THE FROZEN BAND, ~8.9 h: 14 configurations x 6 seeds = 84 rows. The scale
#   axis is dropped deliberately -- it appears in no published number, and this
#   is the suite's dominant stage.

# --- E7: shared-vs-per-camera interface ablation -----------------------------
python -u -m experiments.e7_interface_ablation --force --out "${OUT_DIR}"      # four arms, ~6 min
python -u -m experiments.e7_interface_ablation \
    --seeds 42,43,44,45,46,47,48,49,50,51 --out "${OUT_DIR}"                   # THE BAND, ten seeds, 480 rows
python -u -m experiments.e7_focal_standoff_analysis --out "${OUT_DIR}"         # AFTER the band; reads it by hardcoded path

# --- Standalone analyses -----------------------------------------------------
python -u -m experiments.fd_jacobian_accuracy --out "${OUT_DIR}" --force
python -u -m experiments.reconstruction_bootstrap --out "${OUT_DIR}" --force   # AFTER E2's production run

# --- The gate the driver runs after every stage ------------------------------
python experiments/check_rerun_gates.py "${OUT_DIR}" --profile full
```

Ordering is not cosmetic here: `e4` after E2's production run (or `benchmark_grid.csv` comes
back with nine rows instead of ten, silently), `e7_focal_standoff_analysis` after E7's band,
`reconstruction_bootstrap` after E2's production run, E3's `--check` before its `--force`, and
E6's single-seed run never overlapping its band. §2.4 gives the reasons.

### 7.3 Commands the driver deliberately does NOT run

Everything above is a suite invocation. These four are not, and none of them belongs in a
production run:

```bash
python -m experiments.e2_real_rig                          # the Zenodo path (no config, §3), a reader's default
python -m experiments.e4_benchmark_grid --check --out "${OUT_DIR}"   # re-aggregates only; structurally always red
python -m experiments.render_expectation_sheet --check     # is EXPECTATIONS.md still in step with the manifest?
python -m experiments.render_expectation_sheet --write     # regenerate it after editing the manifest
```

Every committed result carries a provenance record — seed, AquaCal version, git SHA, and the
Python/NumPy/SciPy/OS environment — in one of exactly three shapes; §2.5 enumerates them.
Provenance is asserted mechanically, not by inspection, in
`tests/unit/test_experiments_provenance.py`: the six Phase-19.1 records that predate the seed
key are named there explicitly (see "The seed carve-out"), and a CSV committed without an
entry in that test's `CSV_TO_RECORD` mapping fails CI.

## 8. Pre-fix artifact archive

`experiments/archive/` preserves committed artifacts from before a non-inert fix, so a
reader diffing the manuscript's numbers has one artifact to diff against instead of
reconstructing "before" from git history. See `experiments/archive/README.md` for the
index and the convention (partial copy plus `git show <sha>:<path>` pointers for anything
that trips `check-added-large-files` or `detect-secrets`).
