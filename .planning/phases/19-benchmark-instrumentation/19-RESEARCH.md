# Phase 19: Benchmark Instrumentation - Research

**Researched:** 2026-07-24
**Domain:** Instrumentation of an existing SciPy `least_squares`-based bundle-adjustment
pipeline (solver diagnostics, memory sampling, environment capture, machine-readable
benchmark records) — not new numerical work.
**Confidence:** HIGH (all six priority questions resolved by reading the live source tree,
the live SciPy 1.17.0 install, and the live psutil 7.2.2 install on this machine; no
training-data guesses were needed for the load-bearing claims)

## Summary

Phase 19 is a pure instrumentation phase over four existing `least_squares` call sites and
one existing pipeline orchestration function. Every one of the six research priorities had a
concrete, verifiable answer sitting in the repository or the installed SciPy/psutil source —
this is not a "go find a library" phase, it is a "read the code you already have very
carefully" phase.

The single most important structural finding: **none of the four in-scope call sites can have
their return-tuple signatures changed without breaking public API and multiple call sites**,
because `optimize_interface` and `joint_refinement` are both exported from
`aquacal.calibration.__init__` and unpacked positionally by `pipeline.py` and five+ test
files. The least invasive mechanism — satisfying D-08's "additive capture, not a refactor" —
is a trailing, default-`None`, mutable out-parameter (a dict or small dataclass instance the
caller supplies and the callee populates in place after `least_squares` returns, mirroring the
existing `observer: OptimizerObserver | None = None` pattern already used at two of the four
sites). This adds zero risk to any existing caller and requires zero changes to any existing
return statement.

The second major finding: BENCH-06's "bit-exact" claim is easy to satisfy and even easier to
verify, because SciPy 1.17.0's `least_squares` signature already defaults `ftol=xtol=gtol=1e-8`
as **hardcoded literals**, not `None`-sentinels — there is no internal `if ftol is None` branch
for these three parameters, so passing the identical literal explicitly is provably a no-op by
inspection, not just by testing. `max_nfev` is the one parameter that *is* `None`-sentinelled;
its internal resolution (`max_nfev = x0.size * 100`, in `scipy/optimize/_lsq/trf.py`, both the
bounded and unbounded branches) was located and confirmed live, giving the exact formula
`benchmark.json` must replicate to report `max_nfev`'s effective value honestly.

The third major finding, which changes the recommended implementation for BENCH-02: on
Windows, `psutil.Process().memory_full_info().peak_wset` is a true OS-tracked high-water mark
— confirmed live on this machine, returning distinct `peak_wset`/`wset` fields — meaning **no
polling is required on Windows at all**. On Linux, psutil has never implemented an equivalent
(open upstream issues #1096 and #1540 confirm no peak-RSS field exists in `memory_info()` on
that platform as of current psutil), but the Linux kernel exposes the same concept for free via
`/proc/<pid>/status`'s `VmHWM` line — also zero-polling, zero-distortion. Both platforms in
this project's CI matrix (`ubuntu-latest`, `windows-latest`) therefore have a *non-polling*
path to a genuine peak reading; polling should be reserved as the documented fallback for
platforms with neither (e.g. macOS), not the default implementation.

**Primary recommendation:** Implement BENCH-01/02/03/04/06 as additive, opt-out-of-nothing
instrumentation layered onto the four existing `least_squares` call sites via a new
`SolverDiagnostics` dataclass and a trailing `diagnostics_out` parameter; capture peak RSS via
platform-native zero-polling reads (`peak_wset` on Windows, `VmHWM` via `/proc` on Linux, timed
polling fallback elsewhere) gated by the existing `save_*`-style opt-in flag pattern; and derive
P/group-count/reduction directly from the `jac_sparsity`/`groups` arrays that
`optimize_interface`/`joint_refinement` already build internally, rather than recomputing them.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — Measure process RSS via `psutil`, not `tracemalloc`, and record which mode was
  used.** `psutil` is the primary mode (new optional `[bench]` extra, not core). Falls back to
  `tracemalloc` if `psutil` is missing, and the record honestly labels which mode ran:
  `memory.mode` = `"psutil_rss"` or `"tracemalloc_python_heap"`. `psutil` 7.2.2 is present in
  the dev environment but **not yet declared** in `pyproject.toml`.
- **D-02 — Peak RSS requires sampling, and sampling is opt-in with the flag.** The sampler
  must exist only when the flag is on (never enabled by default, because a sampler carries the
  same timing-distortion hazard the requirement explicitly warns about for `tracemalloc`). The
  sampling mechanism itself (background thread vs. coarse in-loop sampling) is the planner's
  implementation choice — **but see this research's Q3 finding: on Windows and Linux, no
  sampling/polling mechanism is actually needed**, because both platforms expose an
  OS-maintained peak reading directly.
- **D-03 — Nest per-stage metrics under the stage keys Phase 18 just settled.** Reuse
  `stage3_interface_optimization`, `stage3_intrinsic_pass`, `validation` exactly as they
  appear in `pipeline.py`'s `timings` dict. No parallel vocabulary.
- **D-04 — The file carries a `schema_version` integer, starting at `1`.** The aggregator
  (BENCH-05) must refuse to merge records whose `schema_version` it does not recognize.
- **D-05 — Environment capture never fails the run.** `aquacal_version` always recorded.
  `git_sha` best-effort: read if `.git` exists, else `null` + `git_sha_source: "unavailable"`.
- **D-06 — Accuracy fields are copied, never recomputed.** `benchmark.json` reports
  RMS/accuracy values the pipeline already produced; nothing not already computed belongs in
  the record.
- **D-07 — Exactly four call sites are in scope**: `interface_estimation.py:337`
  (`optimize_interface`, Stage 3), `refinement.py:237` (`joint_refinement`, Stage 3's second
  pass), `interface_estimation.py:672` (`register_auxiliary_camera`), `point_refinement.py:674`
  (`refine_calibration`). **Out of scope:** `extrinsics.py:189` and
  `validation/evaluation.py:302` (small inner per-frame PnP LM helpers, called many times per
  run — recording these would bloat the record without informing the paper's performance
  claims).
- **D-08 — Today only `result.status` and `result.message` are read, and only on the failure
  path.** All four sites currently discard `nfev`, `njev`, `cost`, `optimality`. This is
  additive capture, not a refactor of error handling.
- **D-09 — BENCH-06 lands before BENCH-04** (already enforced by phase sequencing — this is
  Phase 19 internally, not a cross-phase constraint at this point).
- **D-10 — The explicit values are SciPy 1.17's current defaults, verified live:**
  `ftol = 1e-8`, `xtol = 1e-8`, `gtol = 1e-8`, `max_nfev = None`. Passing them explicitly must
  be bit-identical, asserted by a regression test comparing `result.x` exactly (not
  approximately). `max_nfev`'s "unset/auto" case must be recorded as such, not silently
  normalized to a number.
- **D-11 — BENCH-06's requirement text uses retired vocabulary.** "Stage 3 and Stage 4" in
  `REQUIREMENTS.md` maps to **Stage 3 and Stage 3's second pass** — i.e. `interface_estimation.py`
  and `refinement.py` only. `point_refinement.py` is NOT a BENCH-06 target site (see Assumptions
  Log / Open Questions — it already partially self-instruments, see Common Pitfalls).
- **D-12 — Standalone scripts under `benchmarks/`, not an `aquacal` CLI subcommand.** The
  `benchmarks/` directory does not exist yet.
- **D-13 — The runner emits both a tidy CSV and a LaTeX table fragment, and computes
  nothing.** Pure aggregator: read every `benchmark.json`, concatenate, emit. Any derived
  quantity (e.g. FD reduction) must already be recorded by the pipeline under BENCH-03, not
  computed by the runner.

### Claude's Discretion

- Sampling mechanism for peak RSS (background thread vs. coarse in-loop sampling) —
  **this research recommends: prefer zero-polling OS-native reads (Windows `peak_wset`, Linux
  `/proc/<pid>/status` VmHWM) where available; fall back to interval polling only where
  neither exists.**
- Exact shape of the `SolverDiagnostics` capture mechanism (out-parameter vs. extended
  observer vs. module collector) — this research recommends a trailing `diagnostics_out`
  parameter (see Q1 findings below).
- D-07's out-of-scope call and D-12's no-CLI-subcommand call are flagged as the next most
  reversible-but-consequential decisions after D-01/D-04, per CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

- Actually reducing memory or CPU during calibration — Phase 19 measures and reports only.
- Correcting BENCH-06's "Stage 4" wording in `REQUIREMENTS.md` — noted but not edited
  unilaterally (D-11).
- "Reduce memory and CPU load during calibration" todo — stays open, addressed only by
  BENCH-02's measurement half.
- "Upload new Zenodo dataset" — belongs to Phase 21, not this phase.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| BENCH-01 | Solver diagnostics (`nfev`, `njev`, `cost`, `optimality`, `status`, message) captured from all four `least_squares` sites | Q1: `diagnostics_out` out-parameter pattern, confirmed non-breaking against all current call sites (see Architecture Patterns, Pattern 1) |
| BENCH-02 | Peak memory per stage, opt-in flag, mode recorded | Q3: `peak_wset` (Windows) / `VmHWM` (Linux) zero-polling reads, verified live on this machine; `tracemalloc` fallback |
| BENCH-03 | P, column-group count, FD reduction, measured from the live run | Q4: `jac_sparsity.shape[1]` and `groups.max()+1` already computed locally inside `optimize_interface`/`joint_refinement` via `build_jacobian_sparsity`/`build_structural_column_groups`; surfaced through the same `diagnostics_out` mechanism |
| BENCH-04 | `benchmark.json` written per run: problem shape, per-stage metrics, solver config, accuracy, environment | D-03/D-05 verbatim + Q5: environment capture recipe (psutil, `platform`, `importlib.metadata`, best-effort git SHA) |
| BENCH-05 | `benchmarks/` runner: CSV + LaTeX fragment, sweeps grid, computes nothing | D-12/D-13 verbatim; `pandas` already a core dependency, no new dependency needed for the CSV/aggregation step |
| BENCH-06 | Stage 3 / Stage 3's second pass pass `ftol`,`xtol`,`gtol` explicitly at SciPy's current effective values; `max_nfev` recorded with effective value; bit-unchanged, regression-tested | Q2: SciPy 1.17.0 source confirms `ftol=xtol=gtol=1e-8` are hardcoded (non-`None`) defaults — explicit pass is provably a no-op; `max_nfev=None` resolves to `x0.size * 100` inside `scipy/optimize/_lsq/trf.py` (both TRF branches) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Solver diagnostics capture (`nfev`, `cost`, etc.) | Calibration/optimization layer (`interface_estimation.py`, `refinement.py`, `point_refinement.py`) | Pipeline orchestration (`pipeline.py`) | The diagnostics originate at the `least_squares` call; the pipeline only aggregates and serializes them |
| Peak memory sampling | Pipeline orchestration (`pipeline.py`, wrapping each `_time_stage` block) | OS/psutil (platform layer) | Per-stage attribution requires the pipeline to know stage boundaries; the actual reading is a thin OS call |
| P / column-group count | Calibration/optimization layer (`_optim_common.py` outputs, surfaced by `interface_estimation.py`/`refinement.py`) | — | These values are structural properties of the Jacobian sparsity pattern built inside the optimizer call, not the pipeline |
| `benchmark.json` assembly & write | Pipeline orchestration (`pipeline.py`, alongside existing `calibration.json`/`diagnostics.json` writers) | I/O helpers (`aquacal.io.internals`, `aquacal.io.serialization`) | Consistent with where `CalibrationResult`/`DiagnosticsData` are already assembled and written |
| Environment capture (CPU/RAM/OS/versions/git) | Pipeline orchestration (`pipeline.py`) or a new small `aquacal.io.environment` module | — | Self-contained, no dependency on optimization internals; best factored as a pure function for testability |
| `benchmarks/` sweep runner (CSV + LaTeX) | New top-level `benchmarks/` directory (outside `src/aquacal`) | `pandas` (already a core dependency) | D-12: explicitly not part of the shipped package's public API |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `psutil` | 7.2.2 (installed; declare `>=5.9` for the `memory_full_info()`/cross-platform API used here) | Peak/current RSS, CPU count, total RAM | D-01 locked choice; only cross-platform library exposing process memory without shelling out |
| `scipy` | 1.17.0 (already required `>=1.16`) | `least_squares` itself, and the source of the `ftol`/`xtol`/`gtol`/`max_nfev` semantics this phase records | Already a core dependency; no version bump needed — `>=1.16` already covers the `callback` parameter Phase 16 needed, and 1.17.0's defaults are unchanged from what `>=1.16` guarantees for these four kwargs |

**Version verification (live, this session):**
```
$ python -c "import scipy; print(scipy.__version__)"
1.17.0
$ python -c "import psutil; print(psutil.__version__)"
7.2.2
$ pip index versions psutil
psutil (7.2.2)  # latest
```

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pandas` | already core dependency | CSV assembly in the `benchmarks/` runner (D-13) | Reading N `benchmark.json` files into a tidy `DataFrame`, then `.to_csv()` |
| stdlib `platform` | stdlib | `platform.processor()`/`platform.system()`/`platform.release()` for CPU/OS strings | Environment capture (BENCH-04); no new dependency |
| stdlib `importlib.metadata` | stdlib | `importlib.metadata.version("aquacal")` | Already the established pattern in `pipeline.py` (5 existing call sites) for `software_version` |
| stdlib `subprocess` | stdlib | Best-effort `git rev-parse HEAD` | D-05: must never raise; wrap in try/except, degrade to `null` |
| stdlib `tracemalloc` | stdlib | Fallback memory mode when `psutil` is absent | D-01 explicit fallback; labelled `"tracemalloc_python_heap"` so it's never confused with the RSS number |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `psutil.memory_full_info().peak_wset` (Windows) / `/proc/<pid>/status` VmHWM (Linux) | Background-thread polling of `memory_info().rss` | Polling is strictly worse: adds a live thread contending for the GIL during the exact window being timed, and can miss a short spike between samples. Zero-polling OS reads have neither problem and are available on both CI platforms (`ubuntu-latest`, `windows-latest`) |
| `resource.getrusage(...).ru_maxrss` | — | Rejected in CONTEXT.md D-01: Unix-only, unavailable on Windows (the primary dev platform) |
| `tracemalloc` as primary | `psutil` (locked) | `tracemalloc` only sees Python-heap allocations; the dominant ~3.6 GB peak is a NumPy C-level `.toarray()` allocation invisible to it |
| Hand-rolled greedy grouping for reporting P/groups | Read `jac_sparsity.shape[1]` / `groups.max()+1` directly from what's already built | Recomputing would violate BENCH-03's "measured from the live run rather than a separate script" and could silently drift from the actual grouping used |
| Custom JSON encoder for numpy types | Explicit `float(...)`/`int(...)`/`.tolist()` casts before `json.dump` | This is the pattern already established and used in `aquacal.validation.conditioning.save_conditioning_report` — no new precedent needed, no custom `JSONEncoder` class to maintain |

**Installation:**
```bash
# pyproject.toml: new [project.optional-dependencies] "bench" extra
pip install aquacal[bench]   # installs psutil
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|--------------|-----------|-------------|
| `psutil` | PyPI | ~17 years (first released 2009) | Very high (top-100 PyPI package; tens of millions/week) | `github.com/giampaolo/psutil` | `[OK]` (verified live: `slopcheck install psutil` → `1 OK`) | Approved |

**Packages removed due to slopcheck `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** none.

`slopcheck` 0.6.1 was installed and run live in this research session (`pip install slopcheck`
succeeded; `slopcheck install psutil` returned `[OK] psutil (pypi)`). `psutil` is also the only
new external package this phase introduces — `pandas` (used by the `benchmarks/` runner) is
already a declared core dependency and needs no new audit. No npm-style `postinstall` script
concept applies to `psutil` (a C-extension PyPI package); its build uses standard
`setup.py`/wheel mechanics with no network calls at install time.

## Architecture Patterns

### System Architecture Diagram

```
run_calibration_from_config(config)
        |
        v
  [Stage 1: intrinsics]  --(timings["stage1_..."])-->
        |
  [Stage 2: pose graph init]
        |
        v
  [Stage 3: optimize_interface()]  <-- interface_estimation.py:337 least_squares(...)
        |         \
        |          `-- (NEW) diagnostics_out populated: nfev, njev, cost,
        |               optimality, status, message, n_params, n_groups
        |          `-- (NEW, opt-in) peak-RSS sample taken around this block
        v
  [Frame rejection + Stage 3 rerun]  (same call site, second invocation)
        |
        v
  [Stage 3's second pass: joint_refinement()]  <-- refinement.py:237 least_squares(...)
        |          `-- (NEW) diagnostics_out populated (same fields)
        v
  [Auxiliary camera registration: register_auxiliary_camera()]  <-- interface_estimation.py:672
        |          `-- (NEW) diagnostics_out populated (no stage number, per D-23 vocabulary)
        v
  [Validation / evaluate_calibration]
        |
        v
  (NEW) assemble_benchmark_record(timings, diagnostics_out map, memory samples,
        P/groups, environment) --> write output_dir/benchmark.json
        |
        v
  (separate, standalone) refine_calibration()  <-- point_refinement.py:674 least_squares(...)
        |          `-- (NEW) diagnostics_out populated; NOT part of benchmark.json —
        |               this function is not called from run_calibration_from_config
        v
  RefinementResult (its own return type; diagnostics surfaced there, not in benchmark.json)


(separate, offline) benchmarks/sweep_runner.py
        |
        v
  glob every output_dir/**/benchmark.json --> pandas.DataFrame --> .csv + .tex fragment
```

### Recommended Project Structure

```
src/aquacal/
├── calibration/
│   ├── _observability.py      # EXTEND: add SolverDiagnostics dataclass + a small
│   │                           #   `capture_solver_diagnostics(result, ftol, xtol, gtol,
│   │                           #   max_nfev, n_params=None, n_groups=None) -> SolverDiagnostics`
│   │                           #   pure helper (no I/O), used at all 4 call sites
│   ├── interface_estimation.py  # MODIFY: 2 call sites (optimize_interface, register_auxiliary_camera)
│   ├── refinement.py            # MODIFY: 1 call site (joint_refinement) + explicit ftol/xtol/gtol
│   ├── point_refinement.py      # MODIFY: 1 call site (refine_calibration)
│   └── pipeline.py              # MODIFY: assemble + write benchmark.json; peak-RSS sampling
├── io/
│   ├── internals.py             # REUSE: ensure_internals_dir/warn_if_overwriting pattern
│   ├── benchmark.py             # NEW: write_benchmark_json(), capture_environment(),
│   │                           #   capture_peak_memory() (platform dispatch)
│   └── serialization.py         # REFERENCE: existing JSON-writer pattern to mirror
├── config/schema.py              # MODIFY: CalibrationConfig gains a `save_benchmark: bool`
│                                  #   (or similarly named) opt-in flag, following the
│                                  #   `save_conditioning`/`save_optimization_trace` pattern
benchmarks/                        # NEW (D-12), repo root, NOT under src/aquacal
├── sweep_runner.py                # Sweeps cameras x frames grid, calls run_calibration_from_config
├── aggregate.py                   # Reads every benchmark.json, emits CSV + .tex fragment
tests/
├── unit/test_observability.py     # EXTEND: SolverDiagnostics capture unit tests
├── unit/test_benchmark.py         # NEW: benchmark.json schema, environment capture,
│                                  #   git_sha degradation, memory-mode labelling
├── unit/test_refinement.py        # EXTEND: bit-exact regression test (BENCH-06)
├── unit/test_interface_estimation.py  # EXTEND: bit-exact regression test (BENCH-06)
```

### Pattern 1: Additive out-parameter for solver diagnostics (Q1 answer)

**What:** Add a trailing, default-`None` parameter to each of the four functions —
`diagnostics_out: SolverDiagnostics | None = None` (or a `dict[str, object]` if the planner
prefers a looser contract) — populated in place immediately after the `least_squares(...)`
call, mirroring the existing `observer: OptimizerObserver | None = None` parameter already
present at 2 of the 4 sites (`optimize_interface`, `joint_refinement`).

**When to use:** Any time a function's return-tuple is public API and cannot be extended
without breaking positional-unpacking callers.

**Why this is the least invasive option, concretely, for this codebase:**
- `optimize_interface` and `joint_refinement` are both exported from
  `aquacal.calibration.__init__.__all__` (confirmed: lines 18/34 import, 50/57 export) and
  unpacked positionally at `pipeline.py:131`, `pipeline.py:1063-1065`
  (`stage3_extrinsics, stage3_distances, stage3_poses, stage3_rms = ...`), and
  `pipeline.py:1253-1259` (5-tuple unpack for `joint_refinement`). A new trailing return value
  breaks every one of those call sites plus the equivalent unpacks in
  `tests/unit/test_interface_estimation.py`, `tests/unit/test_refinement.py`,
  `tests/synthetic/test_full_pipeline.py`, `tests/synthetic/test_per_camera_interface.py`,
  and `tests/synthetic/experiment_helpers.py`.
- `register_auxiliary_camera` returns a *union* return type
  (`tuple[..., float] | tuple[..., float, CameraIntrinsics]`) that already varies by
  `refine_intrinsics` — adding a diagnostics element would create a 3-way union, a strictly
  worse API.
- `refine_calibration` (`point_refinement.py`) is public API (imported by
  `tests/unit/test_point_refinement.py` and, per REQUIREMENTS.md, by external WP consumers via
  the v1.6 Refinement API) — same signature-stability concern.
- A trailing keyword-only `diagnostics_out=None` parameter requires **zero changes** to any
  existing call site, positional or keyword, and is invisible to every existing test unless
  that test opts in.

**Example (illustrative, not exact code to paste):**
```python
# Source: pattern inferred from the existing observer=None convention at
# src/aquacal/calibration/interface_estimation.py:140 and refinement.py:53
@dataclass
class SolverDiagnostics:
    """Terminal scipy.optimize.OptimizeResult fields, captured additively."""
    nfev: int
    njev: int | None          # None when jac is not a callable (2-point FD has no njev)
    cost: float
    optimality: float
    status: int
    message: str
    ftol: float
    xtol: float
    gtol: float
    max_nfev_effective: int   # x0.size * 100 when max_nfev was None; the passed value otherwise
    max_nfev_source: str      # "scipy_auto" | "explicit"
    n_params: int | None = None
    n_groups: int | None = None

def optimize_interface(
    ...,
    observer: OptimizerObserver | None = None,
    shared_interface: bool = True,
    diagnostics_out: SolverDiagnostics | None = None,   # NEW, trailing, default None
) -> tuple[dict[str, CameraExtrinsics], dict[str, float], list[BoardPose], float]:
    ...
    result = least_squares(
        cost_func, x0=initial_params, args=cost_args, method="trf",
        loss=loss, f_scale=loss_scale, bounds=(lower, upper), jac=jac,
        verbose=verbose,
        ftol=1e-8, xtol=1e-8, gtol=1e-8,   # BENCH-06: made explicit, bit-identical to prior default
        **ls_kwargs,
    )
    if diagnostics_out is not None:
        diagnostics_out.nfev = result.nfev
        diagnostics_out.njev = getattr(result, "njev", None)
        diagnostics_out.cost = float(result.cost)
        diagnostics_out.optimality = float(result.optimality)
        diagnostics_out.status = int(result.status)
        diagnostics_out.message = result.message
        diagnostics_out.n_params = jac_sparsity.shape[1]         # already computed above
        diagnostics_out.n_groups = int(build_structural_column_groups(...).max()) + 1  # or reuse the already-built groups array
    if result.status <= 0:
        raise ConvergenceError(...)   # D-08: error path unchanged
    ...
```
A dataclass instance mutated in place avoids the awkwardness of a bare `dict` (typos in keys
are a runtime `AttributeError` instead of a silent no-op) while still being fully additive.

### Pattern 2: Zero-polling peak-RSS capture, platform-dispatched (Q3 answer)

**What:** A small `capture_peak_memory()` helper in a new `aquacal.io.benchmark` (or
similar) module that dispatches by `platform.system()`:

- **Windows:** `psutil.Process().memory_full_info().peak_wset` — a true OS-maintained
  high-water mark. Verified live on this machine:
  ```
  >>> psutil.Process().memory_full_info()
  pfullmem(rss=18956288, vms=8732672, num_page_faults=4740, peak_wset=18956288,
           wset=18956288, peak_paged_pool=158552, paged_pool=158376,
           peak_nonpaged_pool=12232, nonpaged_pool=12232, pagefile=8732672,
           peak_pagefile=8732672, private=8732672, uss=7725056)
  ```
  `peak_wset` and `wset` differ once the process has actually freed memory back below its
  historical peak — this field is a monotonic high-water mark maintained by the Windows kernel,
  not something psutil recomputes.
- **Linux:** read `/proc/<pid>/status`, parse the `VmHWM:` line (kilobytes). psutil itself does
  **not** expose this — confirmed via two still-open upstream feature requests
  (`giampaolo/psutil#1096`, `giampaolo/psutil#1540`) requesting exactly this be added — so this
  read must bypass psutil and go directly to `/proc`. This is still zero-polling and
  zero-distortion; it is a single file read of a value the kernel already tracks.
- **Other platforms (e.g. macOS):** neither mechanism exists; document as the sanctioned
  polling fallback (background thread or coarse loop sample of `psutil.Process().memory_info().rss`
  at a fixed interval, e.g. 100ms), and record `memory.mode` as something distinct (e.g.
  `"psutil_rss_polled"`) so a downstream reader can tell the difference in measurement fidelity.
- **`psutil` unavailable at all:** fall back to `tracemalloc`, per D-01, labelled
  `"tracemalloc_python_heap"`.

**Why this matters given D-02's "must not distort timings" warning:** both `peak_wset` and
`VmHWM` reads are O(1) syscalls/file-reads taken *once* at the end of a stage (or at most a
few times per stage), not a sampling loop running concurrently with the optimization — so
there is no GIL contention, no extra thread, and no risk of missing a spike (the OS already
recorded the true peak continuously). This is strictly better than any polling scheme on the
two platforms the CI matrix (`test.yml`) actually exercises (`ubuntu-latest`, `windows-latest`).

**Recommended sampling cadence if a polling fallback is ever exercised:** if implemented,
poll no more often than every 50-100ms in a daemon thread that is started immediately before
`least_squares(...)` and stopped immediately after — this matches typical profiler polling
intervals and keeps thread-wakeup overhead negligible relative to a multi-minute optimization.

### Pattern 3: P / group-count capture without recomputation (Q4 answer)

**What:** `jac_sparsity` (built via `build_jacobian_sparsity(...)`) and `groups` (built via
`build_structural_column_groups(...)`) are already local variables inside
`optimize_interface` (`interface_estimation.py:301-314`) and `joint_refinement`
(`refinement.py:201-214`), constructed to build the `jac` callable passed to `least_squares`.
`P = jac_sparsity.shape[1]`; `n_groups = int(groups.max()) + 1` (this is exactly the assertion
`tests/unit/test_optim_common.py::TestDocumentedGroupingNumbers` uses: `groups.max() + 1 ==
expected_groups`). No new computation is needed — only capturing these two already-existing
local values into `diagnostics_out` at the point they exist, before either variable falls out
of scope.

`point_refinement.py`'s `_build_point_jac_sparsity` + `make_sparse_jacobian_func` call does
**not** pass a `groups=` argument, so it falls back to SciPy's generic `group_columns()`
colorer internally (inside `make_sparse_jacobian_func`, `_optim_common.py:682-683`) rather than
the structural grouping. Its P/group-count are real numbers but are **not** the numbers pinned
by `TestDocumentedGroupingNumbers` (which is specific to the 673/675/727-parameter Stage-3
layout) — see Open Questions for how this should be scoped in `benchmark.json`.

**FD reduction:** `P / n_groups`, matching `docs/guide/optimizer.md`'s phrasing exactly (e.g.
673/13 ≈ 51.8×). Report this as a derived display value computed by the *writer*, not stored
independently — it is arithmetic on two values already recorded, not a new measurement, so it
does not violate BENCH-05's "computes nothing" constraint for the *runner* (the pipeline, not
the runner, computes it once per run).

### Pattern 4: Environment capture, never-fails (Q5 answer)

**What:** A pure function returning a plain dict, wrapping every external call in
try/except so a partial/degraded record is always better than a crashed run:

```python
# Source: pattern verified live on this machine (Windows 11, Python 3.12.12, conda-forge)
import importlib.metadata
import platform
import subprocess
import numpy as np
import scipy
import cv2
import psutil  # optional; only if the [bench] extra is installed

def capture_environment(repo_hint_path: Path | None = None) -> dict:
    env = {
        "aquacal_version": importlib.metadata.version("aquacal"),  # matches existing pipeline.py pattern
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "opencv_version": cv2.__version__,
        "os": f"{platform.system()} {platform.release()}",
        "cpu_model": platform.processor(),           # e.g. "Intel64 Family 6 Model 154 Stepping 3, GenuineIntel"
        "cpu_count_logical": None,
        "ram_total_bytes": None,
        "git_sha": None,
        "git_sha_source": "unavailable",
    }
    try:
        import psutil
        env["cpu_count_logical"] = psutil.cpu_count(logical=True)
        env["ram_total_bytes"] = psutil.virtual_memory().total
    except ImportError:
        pass
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_hint_path, capture_output=True,
            text=True, timeout=5, check=True,
        ).stdout.strip()
        env["git_sha"] = sha
        env["git_sha_source"] = "git_rev_parse"
    except Exception:
        pass  # stays None / "unavailable" -- D-05: never fails the run
    return env
```

Verified live on this machine: `platform.processor()` returns
`"Intel64 Family 6 Model 154 Stepping 3, GenuineIntel"` — usable as a CPU-model string but not
pretty; document this as the accepted raw form rather than attempting WMI/registry parsing on
Windows (would add complexity and Windows-only code paths for a cosmetic improvement only).
`sys.version`/`platform.python_version()`, `numpy.__version__` (2.4.2 here),
`scipy.__version__` (1.17.0), `cv2.__version__` (4.13.0) were all confirmed live and importable
with zero extra dependencies.

**`repo_hint_path` resolution:** no existing pattern in this codebase captures a git SHA today
(confirmed via repo-wide grep — zero hits for `git_sha`, `subprocess.*git`, or `GitPython`).
Recommend resolving it from `Path(__file__).resolve()` walking upward looking for a `.git`
directory, bounded to a small number of parent levels, rather than assuming the current working
directory is the repo root (a pip-installed package run from an arbitrary directory has no
`.git` at all, which is the expected, common case this must degrade gracefully for).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Peak memory reading on Windows | A polling thread reading `memory_info().rss` | `psutil.Process().memory_full_info().peak_wset` | The OS already tracks this exactly; polling can only approximate it and costs a thread |
| Peak memory reading on Linux | A polling thread | Direct read of `/proc/<pid>/status` `VmHWM:` | Same reasoning; the kernel already maintains this value |
| JSON serialization of numpy scalars | A custom `JSONEncoder` subclass | Explicit `float(...)`/`int(...)`/`.tolist()` casts before `json.dump`, matching `aquacal.validation.conditioning.save_conditioning_report`'s existing pattern | Consistency with an established, tested pattern in this codebase; a custom encoder is one more thing to test and one more place numpy types can leak through un-cast |
| `max_nfev`'s effective value when unset | A magic string like `"auto"` | Compute `x0.size * 100` (verified live in `scipy/optimize/_lsq/trf.py`, both TRF branches) and record it as a number alongside a `max_nfev_source: "scipy_auto"` tag | A magic string is not truthfully "the effective value including the unset/auto case" as BENCH-06 requires — the actual number scipy used is knowable and should be reported |
| Column-group count for P/reduction reporting | Recomputing via a fresh call to `build_structural_column_groups` from `benchmark.json`'s writer, disconnected from the actual optimizer call | Capture the `jac_sparsity`/`groups` arrays already built inside `optimize_interface`/`joint_refinement` at the point of use | BENCH-03 explicitly requires "measured from the live run rather than a separate script"; a disconnected recomputation could silently drift from what was actually run if the two code paths diverge in the future |

**Key insight:** every "don't hand-roll" item above exists because this codebase (or the host
OS) already computes the exact value needed, one level up or down from where the requirement
asks for it to be reported. The entire phase is a wiring exercise, not an algorithm-design
exercise.

## Common Pitfalls

### Pitfall 1: Breaking public API by extending a return tuple

**What goes wrong:** Adding a 5th (or 6th) element to `optimize_interface`'s or
`joint_refinement`'s return tuple silently breaks every positional unpack at every call site,
including test files, with no error until those tests run (or worse, a wrong-shape unpack that
raises `ValueError: too many values to unpack` at import-adjacent code, not at the point of the
actual bug).
**Why it happens:** Tuples are the existing convention for these two functions'
return values; it's tempting to just add one more, especially since the "invisible" narrative
label for the change (a diagnostics field) doesn't feel like it should be a big deal.
**How to avoid:** Use the trailing `diagnostics_out=None` out-parameter pattern (Q1/Pattern 1)
instead of touching the return statement at all.
**Warning signs:** Any plan task that says "add a `diagnostics` field to the return tuple of
`optimize_interface`" should be flagged and rewritten before execution.

### Pitfall 2: `point_refinement.py` already partially sets tolerances — don't double-set or conflate scope

**What goes wrong:** `point_refinement.py:refine_calibration` (line 683-686) already passes
`ftol=ftol, xtol=xtol, max_nfev=effective_max_nfev` explicitly to `least_squares` (with
default values `ftol=1e-8, xtol=1e-8`, verified live via grep at lines 415-417) — but it does
**not** pass `gtol`, and its `max_nfev` auto-scaling formula (`200 * n_params` when
`refine_intrinsics and max_nfev is None`, line 627-630) is a **different multiplier than
scipy's own internal default** (`100 * n_params`). This is a pre-existing, intentional
override, not a bug — but a plan that assumes "point_refinement already does BENCH-06's job"
would be wrong on two counts: (1) `gtol` is still implicit there, and (2) D-11 explicitly says
`point_refinement.py` is **not** one of the two BENCH-06 target sites (only
`interface_estimation.py:337` and `refinement.py:237` are, per the "Stage 3 / Stage 3's second
pass" mapping). Do not fold `point_refinement.py`'s already-explicit tolerances into the
BENCH-06 task; it is separate prior art, not the same requirement.
**Why it happens:** Surface pattern-matching ("explicit ftol/xtol already exist here") without
checking the requirement's exact scope enumeration (D-07).
**How to avoid:** Treat D-07's four-site list and D-11's two-site BENCH-06 subset as
authoritative; do not extend either list by inference.
**Warning signs:** A plan task description that says "point_refinement already satisfies
BENCH-06, verify only" — this conflates two different requirements' site lists.

### Pitfall 3: numpy scalar types are not JSON-serializable

**What goes wrong:** `result.cost`, `result.optimality`, `result.nfev` from SciPy are numpy
scalar types (`np.float64`, `np.int32`/`np.int64` depending on platform), not native Python
`float`/`int`. Passing them directly to `json.dump` raises
`TypeError: Object of type float64 is not JSON serializable`.
**Why it happens:** SciPy's `OptimizeResult` is built from numpy arithmetic internally; nothing
casts its scalar attributes to native Python types before returning.
**How to avoid:** Cast every numeric field explicitly with `float(...)`/`int(...)` before
constructing the dict that gets `json.dump`ped, matching the exact pattern already used in
`aquacal.validation.conditioning.save_conditioning_report` (`condition_number=float(...)`,
`singular_values.tolist()`).
**Warning signs:** A `benchmark.json` writer that does `json.dump(result.__dict__, f)` or
similar without explicit casts will pass on `float`/`linear` results but fail on any
`np.int64` count field, often only surfacing on a different platform where numpy's default
int width differs (`int32` on Windows vs. `int64` on Linux/macOS is a genuine, previously-seen
cross-platform gotcha class in this ecosystem, though not yet observed in this codebase).

### Pitfall 4: Instrumentation overhead changing floating-point results (the Phase 16/17 lesson, reapplied)

**What goes wrong:** Any wrapper around `fun`/`jac`/`callback` that does more than read values
risks perturbing the floating-point path (e.g. an extra `float()` cast changing an operation
order, or timing code that accidentally holds a reference preventing garbage collection of a
large array mid-optimization, changing peak memory itself). Phases 16 and 17 both hit real bugs
in this genre (`shared_interface`-unpack mismatch caused actual divergence, not just a
performance artifact — see `.planning/knowledge-base.md`'s implicit lesson and
`shared-interface-unpack-must-thread-everywhere` in project memory).
**Why it happens:** "Just capture a value" instrumentation is easy to write in a way that
subtly touches the hot path (e.g. constructing a new array from `result.jac` for a "size" log
line before the caller finishes using `result.jac`).
**How to avoid:** Every new read of `result.*` in `diagnostics_out` population code must happen
strictly **after** `least_squares(...)` returns and must only read scalar/small attributes
(`nfev`, `njev`, `cost`, `optimality`, `status`, `message`) — never touch `result.jac`,
`result.fun`, or `result.x` in a way that copies or holds them beyond what the existing code
already does. This mirrors `OptimizerObserver.on_solution`'s own documented discipline ("only a
small `ConditioningReport` survives... `result`/`result.jac` are never retained as attributes").
**Warning signs:** Any diagnostics-capture code that stores a reference to `result` itself
(rather than extracting scalar fields) risks keeping the whole `OptimizeResult` (including
`result.jac`, which can be tens of MB to GB) alive longer than necessary — this is exactly the
kind of accidental retention that inflates the *reported* peak memory number by measurement
artifact rather than genuine algorithmic peak, undermining the very measurement BENCH-02 exists
to produce honestly.
**Verification test:** BENCH-06's regression test (comparing `result.x` exactly across a run
with and without the new explicit `ftol`/`xtol`/`gtol` kwargs and diagnostics capture) already
covers this for the numerical-result side; extend it (or add a sibling test) asserting
`result.nfev`/`result.cost` are also unchanged, since a subtly different `callback`/`jac`
wrapping could change iteration counts even if the final `x` converges to the same point by
luck.

### Pitfall 5: `njev` is not always present

**What goes wrong:** `OptimizeResult.njev` is only populated when `jac` is a callable (not the
string `"2-point"`). All four in-scope call sites use `use_sparse_jacobian=True` by default,
which supplies a callable `jac` (via `make_sparse_jacobian_func`), so `njev` should be present
in the common case — but any call with `use_sparse_jacobian=False` (a real, user-facing
parameter on `optimize_interface`/`joint_refinement`) falls back to `jac="2-point"`, and
`result.njev` may then be `None` or absent depending on the TRF/dogbox code path.
**Why it happens:** SciPy's own docs describe `njev` as conditionally present ("Number of
Jacobian evaluations done. If None (default), it is set to 0.0 for '2-point'.").
**How to avoid:** Use `getattr(result, "njev", None)` defensively rather than `result.njev`
directly, and document the `None` case in `SolverDiagnostics`'s docstring as "not available
when `jac` is `'2-point'`" rather than treating it as a bug.
**Warning signs:** A test that asserts `njev is not None` unconditionally will intermittently
fail depending on `use_sparse_jacobian`.

## Code Examples

### Confirming SciPy 1.17.0's default tolerances (BENCH-06 baseline)

```python
# Source: live introspection this session
import inspect
from scipy.optimize import least_squares
print(inspect.signature(least_squares))
# (fun, x0, jac='2-point', bounds=(-inf, inf), method='trf', ftol=1e-08,
#  xtol=1e-08, gtol=1e-08, x_scale=None, loss='linear', f_scale=1.0,
#  diff_step=None, tr_solver=None, tr_options=None, jac_sparsity=None,
#  max_nfev=None, verbose=0, args=(), kwargs=None, callback=None, workers=None)
```

### Confirming `max_nfev=None`'s resolution (verified against installed SciPy 1.17.0 source)

```python
# Source: scipy/optimize/_lsq/least_squares.py (verified via inspect.getsource this session)
if max_nfev is not None and max_nfev <= 0:
    raise ValueError("`max_nfev` must be None or positive integer.")
# ... passed through unmodified into trf()/dogbox() ...

# Source: scipy/optimize/_lsq/trf.py, both the bounded and unbounded internal branches
# (verified via inspect.getsource this session -- occurs twice, identically, at two
# separate offsets in the same function body)
if max_nfev is None:
    max_nfev = x0.size * 100
```

### Windows peak-RSS field (verified live on this machine)

```python
# Source: live introspection this session, psutil 7.2.2, Windows 11
import psutil
p = psutil.Process()
mi = p.memory_full_info()
print(mi)
# pfullmem(rss=18956288, vms=8732672, num_page_faults=4740, peak_wset=18956288,
#          wset=18956288, peak_paged_pool=158552, paged_pool=158376,
#          peak_nonpaged_pool=12232, nonpaged_pool=12232, pagefile=8732672,
#          peak_pagefile=8732672, private=8732672, uss=7725056)
peak_bytes = mi.peak_wset  # monotonic OS-maintained high-water mark
```

### Linux peak-RSS field (no psutil equivalent; read `/proc` directly)

```python
# Source: confirmed via giampaolo/psutil#1096 and giampaolo/psutil#1540 (open feature
# requests asking for exactly this to be added to psutil's pmem namedtuple on Linux --
# not yet implemented as of psutil 7.2.2)
def linux_peak_rss_bytes(pid: int = None) -> int | None:
    import os
    pid = pid or os.getpid()
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    kb = int(line.split()[1])
                    return kb * 1024
    except FileNotFoundError:
        return None
    return None
```

### Existing numpy-to-JSON cast pattern to mirror (already in this codebase)

```python
# Source: src/aquacal/validation/conditioning.py (existing, tested code -- lines
# 154, 176, 226, 236, 273 per this session's grep)
condition_number = float(s[0] / s[-1])
...
"singular_values": report.singular_values.tolist(),
...
json.dump(payload, f, indent=2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| Only `result.status`/`result.message` read, only on failure | All four call sites will additively capture `nfev`, `njev`, `cost`, `optimality` unconditionally via `diagnostics_out` | This phase (19) | Enables BENCH-01/04's performance record without any behavior change |
| Tolerances entirely implicit (SciPy defaults, never passed) at `interface_estimation.py`/`refinement.py` | Explicit `ftol=1e-8, xtol=1e-8, gtol=1e-8` passed at both sites, `max_nfev` stays implicit but its effective value is computed and recorded | This phase (19) | Satisfies R3.2's request for termination criteria stated by name in the paper supplement |
| No `benchmark.json` artifact exists | Every `run_calibration_from_config` call (opt-in flag) writes `output_dir/benchmark.json` | This phase (19) | Enables BENCH-05's cross-run sweep aggregation |

**Deprecated/outdated:** None — this phase adds capability, it does not replace or retire
anything. `psutil.Process.memory_info_ex()` (deprecated since psutil 4.0.0, in favor of the
current `memory_info()`/`memory_full_info()`) is worth noting as a documentation trap: some
older blog posts and even some AI-generated summaries describe `memory_info_ex()` as the way to
get extended memory fields including a `peak_rss`-like field on Linux — this is **stale**;
current psutil's `memory_info()` on Linux only returns `rss, vms, shared, text, lib, data,
dirty` (no peak field of any kind), confirmed by the still-open upstream feature requests. Do
not implement against `memory_info_ex()`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `platform.processor()`'s raw string (`"Intel64 Family 6 Model 154 Stepping 3, GenuineIntel"`) is an acceptable "CPU model" value for BENCH-04, without further parsing/lookup | Q5 / Code Examples | Low — this is a cosmetic-quality tradeoff, not a correctness one; the paper supplement likely wants a legible CPU name, and this string, while accurate, is not maximally human-friendly. If the user wants a cleaner name (e.g. via `wmic cpu get name` on Windows or `/proc/cpuinfo` `model name` on Linux), that's an easy follow-up, not a blocker |
| A2 | A background-thread polling fallback (for platforms with neither `peak_wset` nor `/proc`) at 50-100ms intervals is an acceptable cadence that does not meaningfully distort stage timings | Architecture Patterns / Pattern 2 | Low-Medium — this path is not expected to be exercised in the project's actual CI matrix (Windows + Linux only), so it is a documented-but-untested fallback; if macOS support is ever added, this cadence should be empirically validated against real stage durations before being trusted |
| A3 | `SolverDiagnostics` as a dataclass (vs. a plain `dict`) is the preferred shape for the out-parameter mechanism | Architecture Patterns / Pattern 1 | Low — this is a naming/ergonomics choice the planner can override; either shape satisfies D-08's additive-capture requirement equally well |

**If this table is empty:** N/A — see entries above. All six numbered research priorities
(Q1-Q6) were resolved by direct code/tool verification (live SciPy source, live psutil output,
live grep of the repository, live `slopcheck` run), not by training-data recall, and are not
listed here.

## Open Questions

1. **Does `point_refinement.py`'s (`refine_calibration`) P/group-count belong in
   `benchmark.json` at all, given it is not called from `run_calibration_from_config`?**
   - What we know: `benchmark.json` is written by the pipeline for a *calibration run*;
     `refine_calibration` is a separate, standalone public API (the v1.6 Refinement API) never
     invoked by `run_calibration_from_config`. Its own diagnostics naturally belong on its own
     `RefinementResult` return value, not nested inside a `benchmark.json` that a given
     `refine_calibration` call may not even produce (no `output_dir` concept is guaranteed to
     exist in its calling context — check `RefinementResult`'s fields before assuming one).
   - What's unclear: whether BENCH-01's "captured from every `least_squares` call" implies these
     diagnostics must *also* be exposed as a documented field on `RefinementResult`, and whether
     that's this phase's job or DOCS-05's (which is explicitly scoped to document
     "the benchmark.json schema" — `refine_calibration`'s diagnostics are arguably a different
     surface).
   - Recommendation: capture the diagnostics at this site (satisfies BENCH-01's four-site
     enumeration literally) and surface them as a new optional field on `RefinementResult`
     (e.g. `solver_diagnostics: SolverDiagnostics | None`), separate from `benchmark.json`. Flag
     this split explicitly in the plan so DOCS-05 knows to document two surfaces, not one.

2. **Should `benchmark.json`'s P/group-count block include `register_auxiliary_camera`'s
   6-or-10-parameter optimization?**
   - What we know: `register_auxiliary_camera` doesn't use the sparse-Jacobian/column-grouping
     machinery at all (per the earlier read, it calls `least_squares` with no `jac=` argument,
     i.e. plain dense 2-point FD over 6-10 parameters) — there is no "P/group-count" concept to
     report there in the first place, only `nfev`/`cost`/etc.
   - What's unclear: whether BENCH-03's P/group-count section of `benchmark.json` should have an
     explicit "N/A, not applicable to this call site" entry for auxiliary registration, or
     simply omit it.
   - Recommendation: omit it from the P/group-count block (it genuinely doesn't apply), but
     still include auxiliary registration's `nfev`/`cost`/etc. under BENCH-01's solver
     diagnostics block, tagged with the no-stage-number label from `18-02-SUMMARY.md`
     ("Auxiliary camera registration").

3. **Exact opt-in flag name and default for BENCH-02's memory sampling / BENCH-04's
   `benchmark.json` writing.**
   - What we know: the established config-flag naming convention is `save_<noun>` (e.g.
     `save_optimization_trace`, `save_conditioning`, `save_stage_calibrations`), all opt-in
     (`False` default) except `save_stage_calibrations` (default `True`).
   - What's unclear: whether `benchmark.json` writing itself should be default-on (like
     `save_stage_calibrations`, since it's cheap and BENCH-04 doesn't warn about cost) while
     only the *memory* sub-block within it is gated behind a separate opt-in flag (since D-02
     specifically warns about sampling cost) — i.e. two flags, not one.
   - Recommendation: two flags — `save_benchmark: bool = True` (writes `benchmark.json`
     unconditionally with everything except memory) and a nested opt-in
     `benchmark_memory: bool = False` (or similar) gating only the peak-RSS capture, consistent
     with D-02's explicit "never enabled by default" instruction applying specifically to the
     memory measurement, not the whole record.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| `psutil` | BENCH-02 (memory mode), BENCH-04 (CPU count, RAM) | Yes (installed in dev env, not yet declared) | 7.2.2 | `tracemalloc` (memory only); `platform`-only environment capture (no cpu_count/ram) |
| `git` CLI | BENCH-04 (`git_sha`) | Yes (repo is a git checkout) | not version-checked (only `rev-parse` used) | `git_sha: null`, `git_sha_source: "unavailable"` (D-05, always available) |
| `scipy` | BENCH-06 (tolerance defaults), all four call sites | Yes | 1.17.0 (already `>=1.16` core requirement) | none needed — already core |
| `pandas` | BENCH-05 (`benchmarks/` runner CSV) | Yes | already core dependency | none needed |
| `slopcheck` | Package legitimacy audit (this research session only, not a runtime dependency) | Yes (installed this session) | 0.6.1 | N/A — dev-tooling only |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `psutil` (falls back to `tracemalloc`, per D-01);
`git` (falls back to `null`/`"unavailable"`, per D-05).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (marker config in `pyproject.toml` `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `markers = ["slow: ..."]`) |
| Quick run command | `python -m pytest tests/ -m "not slow"` |
| Full suite command | `python -m pytest tests/` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| BENCH-01 | `SolverDiagnostics` captured correctly at each of the 4 call sites (nfev/njev/cost/optimality/status/message match `result.*`) | unit | `pytest tests/unit/test_observability.py -k diagnostics -x` | ❌ Wave 0 (extend `test_observability.py` or new file) |
| BENCH-02 | Peak-RSS mode correctly labelled (`psutil_rss` vs `tracemalloc_python_heap`); zero-polling reads return a plausible value on the current platform | unit | `pytest tests/unit/test_benchmark.py -k memory -x` | ❌ Wave 0 (new file) |
| BENCH-03 | P/group-count in `benchmark.json` matches `TestDocumentedGroupingNumbers`'s pinned values for the 13-camera/100-frame synthetic rig | unit | `pytest tests/unit/test_optim_common.py::TestDocumentedGroupingNumbers -x` (existing) + a new cross-check that the pipeline-captured value matches | ✅ (existing test); ❌ new cross-check |
| BENCH-04 | `benchmark.json` round-trips (write, then load, schema_version present, environment never-null on aquacal_version) | unit + integration | `pytest tests/unit/test_benchmark.py -k schema -x` ; `pytest tests/synthetic/test_full_pipeline.py -k benchmark -x` | ❌ Wave 0 |
| BENCH-05 | `benchmarks/aggregate.py` reads N synthetic `benchmark.json` fixtures, emits correct CSV row count and refuses on unknown `schema_version` | unit (new, outside `src/aquacal`, needs its own small test dir or inline pytest under `benchmarks/tests/` or `tests/unit/test_benchmarks_runner.py`) | `pytest tests/unit/test_benchmarks_runner.py -x` | ❌ Wave 0 |
| BENCH-06 | Bit-exact regression: `result.x`, `result.nfev`, `result.cost` identical with vs. without explicit `ftol`/`xtol`/`gtol` at both target sites | unit (exact equality, not approx) | `pytest tests/unit/test_interface_estimation.py -k bit_exact -x` ; `pytest tests/unit/test_refinement.py -k bit_exact -x` | ❌ Wave 0 (extend existing files) |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/ -m "not slow"`
- **Per wave merge:** `python -m pytest tests/` (full suite, including `slow`-marked
  synthetic optimization tests — this phase's bit-exact regression tests should NOT be marked
  `slow`, since they compare deterministic small-problem results, matching the precedent set by
  Phase 16/17's own bit-exact tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_benchmark.py` — new file, covers BENCH-02/BENCH-04's `benchmark.json`
  schema, environment capture (including forced git-unavailable and forced psutil-unavailable
  paths), and memory-mode labelling
- [ ] `tests/unit/test_benchmarks_runner.py` — new file, covers BENCH-05's aggregator against
  small fixture `benchmark.json` files (including a deliberately-mismatched
  `schema_version` to assert the aggregator refuses loudly)
- [ ] Extend `tests/unit/test_observability.py` (or add a sibling) — covers BENCH-01's
  `SolverDiagnostics` capture
- [ ] Extend `tests/unit/test_interface_estimation.py` and `tests/unit/test_refinement.py` —
  BENCH-06's exact-equality regression tests (compare `result.x`/`nfev`/`cost` with explicit
  vs. implicit tolerances)
- [ ] No new framework install needed — pytest is already configured and used throughout

## Project Constraints (from CLAUDE.md)

- Environment: Git Bash (MINGW64) with `/c/Users/...` paths; do not prefix commands with `cd
  /c/Users/.../AquaCal &&` (working directory already starts at project root).
- All internal values in meters; millimeters only for human-readable/display output — this
  phase's `internals`/`benchmark.json` writers should keep memory in bytes (not a unit-system
  concern, but confirm no meters/millimeters values leak into `benchmark.json` unconverted, e.g.
  if any accuracy field is copied from `DiagnosticsData` verbatim per D-06, it is already in
  the correct unit — pixels for reprojection RMS, meters for 3D validation error — no
  conversion needed at the `benchmark.json` layer).
- `interface_distance`/`water_z` naming convention: not directly relevant to this phase's
  scope (no new interface-distance semantics are introduced), but any diagnostics label
  referencing `water_z` (e.g. inside `SolverDiagnostics` or trace output) must not be confused
  with a per-camera physical gap.
- Coordinate system, extrinsics convention: not touched by this phase.
- Testing layout: `tests/unit/` one file per source module (or an extension of an existing
  file when adding to an existing module, e.g. `_observability.py`); `tests/synthetic/` for
  full-pipeline integration; `python -m pytest tests/ -m "not slow"` for fast iteration.
- Always run any real calibration invocation with `python -u`, unbuffered, in the background,
  given the 48-87 minute real-rig runtime — directly relevant if this phase's plan includes a
  human-verify task that runs `run_calibration_from_config` on the real rig to sanity-check
  `benchmark.json`'s memory/timing fields against the known ~3.6 GB peak.
- Ruff formatting, Google-style docstrings, `NDArray` type hints with shapes — applies to all
  new code in this phase (`SolverDiagnostics`, `capture_environment`, `capture_peak_memory`,
  the `benchmarks/` runner scripts).
- `__init__.py` / `__all__` requirement: any new public name (e.g. if `SolverDiagnostics` or
  `capture_environment` is meant to be part of the public API rather than a private
  underscore-prefixed helper) must be added to the relevant package's `__init__.py` and
  `__all__`. Given D-12's no-CLI-subcommand and this being primarily internal instrumentation,
  recommend keeping new helpers private (`_benchmark.py`-style module) unless a genuine
  external use case for calling them directly is identified during planning.

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so treated as enabled per
protocol — but this phase has essentially no attack surface: it is a research-instrumentation
library with no network I/O, no authentication, no user-supplied untrusted input beyond
existing config-file parsing (already covered by prior phases), and no new external package
beyond `psutil` (a mature, extremely widely-used C-extension library, audited above).

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | No | N/A — no auth surface |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Marginal | `benchmark.json` fields are all internally-produced (numbers, version strings); the one external input is `git rev-parse` output, already wrapped in try/except with a 5s timeout to avoid hanging on a misconfigured/huge repo |
| V6 Cryptography | No | N/A — no crypto in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-------------------------|
| Subprocess call to `git` with attacker-controlled `cwd` or environment | Tampering | Not applicable in this codebase's threat model (single-user research library, `cwd` is always the local repo path resolved from `__file__`, not user input); still, wrap in `try/except` + `timeout=5` as a robustness (not security) measure per D-05 |
| Reading arbitrary `/proc/<pid>/status` paths | Information disclosure | Only ever read the *current* process's own `/proc/<self>/status` (`os.getpid()`), never an attacker-supplied PID |

## Sources

### Primary (HIGH confidence)
- Live SciPy 1.17.0 installation on this machine — `inspect.signature(least_squares)`,
  `inspect.getsource` of `scipy/optimize/_lsq/least_squares.py` and
  `scipy/optimize/_lsq/trf.py` (confirms `ftol=xtol=gtol=1e-8` hardcoded, `max_nfev=None ->
  x0.size * 100`)
- Live psutil 7.2.2 installation on this machine — `Process().memory_full_info()` output
  showing `peak_wset`/`wset` fields on Windows
- This repository's own source: `src/aquacal/calibration/interface_estimation.py`,
  `refinement.py`, `point_refinement.py`, `pipeline.py`, `_observability.py`,
  `_optim_common.py`, `config/schema.py`, `io/internals.py`,
  `validation/conditioning.py`, `pyproject.toml`, `.planning/knowledge-base.md`
- `.planning/phases/18-documentation-corrections-stage-model-reconciliation/18-02-SUMMARY.md`
  — the settled stage vocabulary contract, verbatim manuscript citations
- Live `slopcheck 0.6.1` run this session: `slopcheck install psutil` → `[OK]`
- Live `pip index versions psutil` this session: confirms 7.2.2 is latest

### Secondary (MEDIUM confidence)
- [giampaolo/psutil#1096 — "RFE: return max/peak RSS usage from Process.memory_info"](https://github.com/giampaolo/psutil/issues/1096) — corroborates that Linux peak-RSS is not exposed by psutil (still open)
- [giampaolo/psutil#1540 — "[Linux] provide more memory statistics (peak rss mainly)"](https://github.com/giampaolo/psutil/issues/1540) — corroborates the same, more recent and specific to Linux
- [psutil documentation](https://psutil.readthedocs.io/) — general API reference for `memory_info()`/`memory_full_info()` field sets

### Tertiary (LOW confidence)
- General web-search summaries describing `memory_info_ex()` and `/proc/<pid>/status` VmHWM
  behavior — cross-verified against the live psutil source/behavior above (VmHWM's existence in
  `/proc` is well-established Linux kernel documentation, not psutil-specific, and was not
  independently re-verified against a live Linux machine in this session since the dev platform
  is Windows; treat the exact `/proc` parsing recipe as MEDIUM confidence pending a Linux CI
  run, not LOW, since it rests on long-stable, widely-documented `/proc` filesystem behavior
  rather than a single blog post).

## Metadata

**Confidence breakdown:**
- Standard stack (psutil, scipy version behavior): HIGH — verified live against installed
  versions, not training data
- Architecture (out-parameter pattern, call-site blast radius): HIGH — verified by direct
  repository grep of every call site and every `__init__.py` export
- Pitfalls (numpy JSON serialization, njev availability, return-tuple breakage): HIGH for the
  numpy/tuple findings (verified against live code and SciPy docs); MEDIUM for the
  `njev`-availability claim (matches SciPy's documented behavior for `'2-point'` jac, not
  independently re-executed against a live `"2-point"` call in this session)
- Linux peak-RSS recipe (`/proc` VmHWM): MEDIUM — well-established kernel/proc behavior,
  corroborated by two independent open psutil issues, but not executed against a live Linux
  machine in this session (dev platform is Windows)

**Research date:** 2026-07-24
**Valid until:** 2026-08-24 (30 days — SciPy/psutil internals are stable; the one
fast-moving risk is a future psutil release finally closing #1096/#1540 and adding a
cross-platform `peak_rss` field, at which point the Linux-specific `/proc` workaround in this
research becomes unnecessary but not incorrect)
