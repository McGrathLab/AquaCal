# Phase 19: Benchmark Instrumentation - Context

**Gathered:** 2026-07-24
**Status:** Ready for planning

> **How this context was gathered.** The user authorized autonomous execution of Phase 19
> while away ("jump into phase 19... but don't push it if there's a real human gate"), so
> this discussion ran in auto mode: Claude selected every option rather than asking. Each
> decision below records its reasoning so the user can overturn any of them cheaply.
> **D-01 and D-04 are the two worth a deliberate look** — they are flagged inline.

<domain>
## Phase Boundary

Every calibration run — real-rig and synthetic — produces a trustworthy, machine-readable
performance record that a sweep can aggregate without hand computation.

This phase **instruments and records**. It does not optimize anything. Making calibration
faster or lighter is explicitly *not* in scope (see Deferred Ideas / D-09).

Requirements: BENCH-01 through BENCH-06.

</domain>

<decisions>
## Implementation Decisions

### Peak memory measurement (BENCH-02)

- **D-01 — Measure process RSS via `psutil`, not `tracemalloc`, and record which mode was
  used.** ⚠️ *Flagged for user review — this is the most consequential call in the phase.*

  BENCH-02 requires "the measurement mode recorded alongside the number". The three
  candidates are not equivalent, and the obvious stdlib choice is the wrong one:

  | Mode | Sees the real peak? | Cross-platform? | Cost |
  |------|--------------------|-----------------|------|
  | `tracemalloc` | **No** — Python-heap allocations only | Yes | stdlib; distorts timings |
  | `resource.getrusage(...).ru_maxrss` | Yes | **No — Unix only** | stdlib |
  | `psutil.Process().memory_info().rss` | Yes | Yes | new dependency |

  AquaCal's ~3.6 GB peak is dominated by the dense `.toarray()` Jacobian — a NumPy
  C-level allocation that `tracemalloc` does not observe at all. Reporting a tracemalloc
  number would be precise and misleading, which is worse than reporting nothing.
  `resource` is unavailable on Windows, this project's primary development platform.

  **Decision:** `psutil` RSS as the primary mode. Declare it as an *optional* extra
  (`[bench]`), not a core dependency — a benchmarking aid should not become a hard install
  requirement for a calibration library about to cut a release. If `psutil` is missing, fall
  back to `tracemalloc` and label the record honestly. `benchmark.json` records
  `memory.mode` as `"psutil_rss"` or `"tracemalloc_python_heap"` so a downstream reader can
  never confuse the two.

  Note: `psutil` 7.2.2 is already present in the dev environment but is **not** declared in
  `pyproject.toml` — the planner must add the extra, not assume availability.

- **D-02 — Peak RSS requires sampling, and sampling is opt-in with the flag.** RSS is an
  instantaneous reading, so a true per-stage peak needs polling rather than a before/after
  pair. The planner should treat the sampling mechanism (background thread vs. coarse
  in-loop sampling) as an implementation choice, but the sampler must exist **only** when
  the flag is on — BENCH-02 says "never enabled by default, because `tracemalloc` distorts
  the timings being measured", and a polling thread carries the same hazard.

### `benchmark.json` shape (BENCH-04)

- **D-03 — Nest per-stage metrics under the stage keys Phase 18 just settled.** The
  `timings` dict in `pipeline.py` is already keyed `stage3_interface_optimization`,
  `stage3_intrinsic_pass`, `validation`. `benchmark.json` reuses those exact keys rather
  than inventing a parallel vocabulary. This is the entire reason Phase 18 was sequenced
  before Phase 19 — do not reintroduce a second naming scheme.

- **D-04 — The file carries a `schema_version` integer, starting at `1`.** ⚠️ *Flagged.*
  BENCH-05 aggregates many `benchmark.json` files produced over time, possibly across a
  sweep that spans days and a code change. Without a version field, a mid-sweep schema
  change silently produces a CSV with mixed semantics and no way to detect it. The
  aggregator must refuse — loudly — to merge records whose `schema_version` it does not
  recognize, rather than coercing them.

- **D-05 — Environment capture never fails the run.** Record `aquacal_version` always. Get
  `git_sha` best-effort: read it if `.git` exists, otherwise write `null` and set
  `git_sha_source: "unavailable"` (the normal case for a PyPI install). A benchmark record
  that cannot be written because a calibration was run outside a git checkout is a
  self-inflicted wound.

- **D-06 — Accuracy fields are copied, never recomputed.** BENCH-05 says the runner computes
  "nothing the pipeline did not record". The same discipline applies one level up:
  `benchmark.json` reports RMS/accuracy values the pipeline already produced. If a number
  is not already computed during the run, it does not belong in the record.

### Solver diagnostics (BENCH-01)

- **D-07 — Exactly four call sites are in scope**, matching BENCH-01's own enumeration:
  - `src/aquacal/calibration/interface_estimation.py:337` — Stage 3
  - `src/aquacal/calibration/refinement.py:237` — Stage 3's second pass (the intrinsic pass)
  - `src/aquacal/calibration/interface_estimation.py:672` — interface estimation
  - `src/aquacal/calibration/point_refinement.py:674` — point refinement

  **Out of scope:** `extrinsics.py:189` and `validation/evaluation.py:302`. Both are small
  inner Levenberg-Marquardt helpers (per-frame PnP), called many times per run. Recording
  diagnostics for them would bloat the record without informing the paper's performance
  claims. If the planner disagrees, that is a scope change to raise, not to absorb.

- **D-08 — Today only `result.status` and `result.message` are read, and only on the failure
  path.** All four sites currently discard `nfev`, `njev`, `cost`, and `optimality` entirely.
  This is additive capture, not a refactor of the error handling.

### Explicit tolerances (BENCH-06)

- **D-09 — BENCH-06 lands before BENCH-04.** Already a binding constraint recorded in
  `REQUIREMENTS.md` § Cross-cutting #5: `OptimizeResult` does not report termination
  tolerances back, so `benchmark.json` can only record what the caller passed. Until the
  stages set them explicitly, the "solver configuration in force" block is inferred from
  SciPy's defaults rather than observed.

- **D-10 — The explicit values are SciPy 1.17's current defaults, verified live:**
  `ftol = 1e-8`, `xtol = 1e-8`, `gtol = 1e-8`, `max_nfev = None`. Passing them explicitly
  must be bit-identical, asserted by a regression test comparing `result.x` exactly — not
  approximately. `max_nfev`'s "unset/auto" case must be recorded as such rather than
  silently normalized to a number.

- **D-11 — BENCH-06's requirement text uses retired vocabulary.** It reads "Stage 3 and
  Stage 4 pass `ftol`, `xtol`, and `gtol`". Phase 18 retired "Stage 4"; the intended target
  is **Stage 3's second pass**, i.e. `refinement.py`. `REQUIREMENTS.md` was not swept during
  Phase 18 because `.planning/` was deliberately preserved as a historical record (D-18).
  The planner should read BENCH-06 with this mapping and **not** treat "Stage 4" as evidence
  that the four-stage model survives anywhere. Flagged for the user: BENCH-06's wording in
  `REQUIREMENTS.md` may be worth a one-line correction, but it was not edited unilaterally.

### The `benchmarks/` runner (BENCH-05)

- **D-12 — Standalone scripts under `benchmarks/`, not an `aquacal` CLI subcommand.**
  BENCH-05 is a research harness for producing one paper's tables. A new CLI subcommand
  would expand the shipped public API surface immediately before the release cut (Phase 22),
  oblige documentation in Phase 21, and commit the project to supporting a sweep runner as a
  user-facing feature forever. Keeping it in `benchmarks/` costs nothing and keeps the
  package surface unchanged. The directory does not exist yet.

- **D-13 — The runner emits both a tidy CSV and a LaTeX table fragment, and computes
  nothing.** It is an aggregator: read every `benchmark.json`, concatenate, emit. Any
  derived quantity it appears to need (e.g. FD reduction) must instead be recorded by the
  pipeline under BENCH-03.

### Claude's Discretion

Every decision above was made by Claude in auto mode. The ones with genuine alternatives
worth the user's attention are marked ⚠️ (D-01 psutil-vs-tracemalloc, D-04 schema
versioning). D-07's out-of-scope call and D-12's no-CLI-subcommand call are the next most
reversible-but-consequential.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and sequencing
- `.planning/REQUIREMENTS.md` § Benchmarks — BENCH-01 through BENCH-06 verbatim
- `.planning/REQUIREMENTS.md` § Cross-cutting constraint #5 — the BENCH-06 → BENCH-04
  ordering constraint and the 2026-07-24 verification that no stage currently sets tolerances
- `.planning/ROADMAP.md` § Phase 19 — goal and the five success criteria

### Stage vocabulary (settled in Phase 18 — do not reopen)
- `.planning/phases/18-documentation-corrections-stage-model-reconciliation/18-02-SUMMARY.md`
  — the authoritative three-stage / best-first string contract with verbatim manuscript
  citations. Any stage key written into `benchmark.json` must match it.
- `.planning/phases/18-documentation-corrections-stage-model-reconciliation/18-VERIFICATION.md`
  — confirms `src/` is free of Stage-4 vocabulary as of 2026-07-24

### Existing instrumentation to extend, not duplicate
- `src/aquacal/calibration/_observability.py` — `OptimizerObserver`, per-iteration CSV traces
  (Phase 16 / HOOK). Already captures `nfev` and `cost` per iteration via SciPy's `callback`.
- `src/aquacal/validation/conditioning.py` — conditioning diagnostics (Phase 16 / HOOK-03).
  Uses blocked tall-skinny QR + a single SVD, **not** `eigh(J.T @ J)`.
- `src/aquacal/io/internals.py` — `ensure_internals_dir`, `warn_if_overwriting`. The
  established pattern for writing machine-readable artifacts into `output_dir`.

### Project conventions
- `CLAUDE.md` — coordinate conventions, units (meters internally), testing layout.
  **Note: gitignored** (`.gitignore:216`); edits to it are local-only.
- `.claude/rules/code-style.md` — Ruff, Google docstrings, `NDArray` type hints
- `.claude/rules/source-code.md` — `__init__.py` public API and `__all__` requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`timings` dict in `pipeline.py`** (`_time_block` context manager, line ~614): already
  accumulates per-stage wall time under the settled stage keys. `benchmark.json`'s per-stage
  block should be built from this, not from a new timing mechanism.
- **`internals/` output infrastructure** (`ensure_internals_dir`, `warn_if_overwriting`):
  the existing, tested pattern for emitting machine-readable files into `output_dir`.
  BENCH-04 writes `benchmark.json` to `output_dir` itself (not `internals/`), but should
  reuse the overwrite-warning discipline.
- **`OptimizerObserver`** (`_observability.py`): already hooks SciPy's `callback` and reads
  `nfev`/`cost` per iteration. BENCH-01 needs *terminal* values from the returned
  `OptimizeResult`, which is a different and simpler capture — do not conflate them.
- **Config `internals` block** (`pipeline.py` ~line 427): `save_stage_calibrations`,
  `save_optimization_trace`, `save_conditioning`. BENCH-02's opt-in memory flag belongs
  alongside these, following the same `data.get("internals", {})` pattern.

### Established Patterns
- **Opt-in observability defaults to off** and is threaded from config through the pipeline —
  the pattern Phase 16 established and Phase 17 followed. BENCH-02 must match it.
- **Zero-numerical-change is provable, not asserted.** Phases 16 and 17 both guarded
  instrumentation with bit-exact regression tests. BENCH-06 explicitly demands the same.
- **`scipy>=1.16` is already required** (for the `callback` parameter). Environment is on
  SciPy 1.17.0.

### Integration Points
- Four `least_squares` call sites (D-07) need terminal-diagnostic capture threaded back to
  the pipeline, which currently only receives poses/results.
- `pipeline.py`'s config parsing gains a benchmark/memory flag.
- `pyproject.toml` gains a `[bench]` optional-dependency extra for `psutil`.
- New `benchmarks/` directory at repo root — currently absent.

</code_context>

<specifics>
## Specific Ideas

The paper supplement is the consumer of record for this phase: BENCH-06 exists because
reviewer comment R3.2 asks for termination criteria by name, and BENCH-05's LaTeX fragment
is destined for a table in the manuscript. The hard deadline is the revised SoftwareX
manuscript on 2026-08-21.

Practical consequence: a sweep entry that cannot be traced back to an exact code state is
useless for the paper. That is what makes D-05 (`git_sha` best-effort but always recorded
with its provenance) and D-04 (`schema_version`) load-bearing rather than housekeeping.

</specifics>

<deferred>
## Deferred Ideas

- **Actually reducing memory/CPU during calibration.** Phase 19 measures and reports the
  peak; it does not shrink it. This is an explicit, recorded PROJECT.md decision, not an
  oversight.
- **Correcting BENCH-06's "Stage 4" wording in `REQUIREMENTS.md`** (see D-11). A one-line
  edit, deliberately not made unilaterally.

### Reviewed Todos (not folded)

Auto mode's default rule is to fold every todo scoring ≥ 0.4. Both matches were reviewed and
**neither was folded** — applying that rule here would have contradicted recorded project
decisions and quietly widened the phase.

- **"Reduce memory and CPU load during calibration"** (score 0.9, area: performance) — the
  keyword overlap is real but inverted. `STATE.md` records: *"v1.9 measures and reports this
  peak but does not reduce it — deliberate, see PROJECT.md Key Decisions. Stays open."*
  Phase 19 satisfies the *measurement* half via BENCH-02. The todo stays open.
- **"Upload new Zenodo dataset with image-based inputs"** (score 0.6, area: docs) —
  `STATE.md` assigns this to Phase 21 (DATA-01/02/03) with a sequencing constraint (after
  all code phases + DOCS-06, before DOCS-07) and says *"do not action standalone"*.

</deferred>

---

*Phase: 19-Benchmark Instrumentation*
*Context gathered: 2026-07-24*
