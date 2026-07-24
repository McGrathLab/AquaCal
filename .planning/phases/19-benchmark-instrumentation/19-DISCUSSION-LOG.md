# Phase 19: Benchmark Instrumentation — Discussion Log

**Date:** 2026-07-24
**Mode:** `--auto` (Claude selected every option; no questions were put to the user)

> Human reference only. Downstream agents read `19-CONTEXT.md`, not this file.

## Why auto mode

The user authorized autonomous execution before stepping away: *"when phase 18 completes,
jump into phase 19. I am going to lunch, hoping you can have phase 19 done when I get back,
but don't push it if there's a real human gate you need confirmation on."*

Running the standard interactive discussion would have blocked the entire window and
delivered nothing. Running auto mode delivers a plannable phase with every judgment call
recorded and reversible. Two decisions are flagged ⚠️ in CONTEXT.md as worth a deliberate
look; the rest are low-regret.

This is a deviation from the user's recorded preference for discussing design tradeoffs in
prose before choosing ([[prefers-discussing-design-decisions]]). The mitigation is that each
decision in CONTEXT.md carries its full reasoning and the alternatives considered, so
overturning one costs a sentence rather than a re-derivation.

## Areas analyzed

| Area | Outcome |
|------|---------|
| Peak memory measurement mode | D-01, D-02 — ⚠️ flagged |
| `benchmark.json` schema shape | D-03, D-04 (⚠️ flagged), D-05, D-06 |
| Solver diagnostic call-site scope | D-07, D-08 |
| Explicit tolerances and ordering | D-09, D-10, D-11 |
| Sweep runner packaging | D-12, D-13 |

## Judgment calls and their alternatives

### Peak memory: psutil over tracemalloc (D-01)

The stdlib-first instinct picks `tracemalloc`. That would have been wrong. AquaCal's ~3.6 GB
peak lives in the dense `.toarray()` Jacobian — a NumPy C-level allocation `tracemalloc`
cannot see. The reported number would have been precise, small, and misleading.

`resource.getrusage(...).ru_maxrss` sees the true peak and is stdlib, but is Unix-only, and
this project is developed on Windows 11. It would have failed on the user's own machine.

`psutil` was chosen and confined to an optional `[bench]` extra so a benchmarking aid does
not become a hard install requirement for a calibration library about to cut a release.
Fallback to `tracemalloc` is explicit and labelled in the record.

*Reversible at low cost — swap the sampler and the mode label.*

### Schema versioning (D-04)

Not requested by any requirement. Added because BENCH-05 aggregates many files produced over
a sweep that may span days and a code change; without a version field, mixed-semantics rows
merge silently into the paper's table. The aggregator refuses unknown versions loudly.

*Cheap now, expensive to retrofit after a sweep has run.*

### Four call sites, not six (D-07)

BENCH-01 enumerates four solver call sites. The codebase has seven `least_squares` calls.
`extrinsics.py:189` and `validation/evaluation.py:302` are per-frame Levenberg-Marquardt
helpers invoked many times per run; instrumenting them would bloat the record without
informing any performance claim in the paper. Recorded as a scope boundary the planner
should raise rather than absorb if it disagrees.

### No `aquacal bench` subcommand (D-12)

A CLI subcommand would expand the shipped public API right before the Phase 22 release cut,
require documentation in Phase 21, and commit the project to supporting a research sweep
runner as a user-facing feature. Standalone scripts under `benchmarks/` cost nothing.

## Todos reviewed — both rejected against auto-mode's own rule

Auto mode folds every todo scoring ≥ 0.4. Both matches cleared that bar and both were
rejected, because folding them would have contradicted decisions already recorded in
`STATE.md` and `PROJECT.md`:

- **Reduce memory/CPU during calibration** (0.9) — v1.9 measures this peak, deliberately does
  not reduce it. High keyword overlap, inverted intent.
- **Upload new Zenodo dataset** (0.6) — assigned to Phase 21 with an explicit
  "do not action standalone" note.

Mechanical rule-following would have widened Phase 19 twice over.

## Discovered during analysis, not acted on

- **BENCH-06's requirement text still says "Stage 4"** — vocabulary Phase 18 retired. The
  intended target is Stage 3's second pass (`refinement.py`). `REQUIREMENTS.md` was not
  swept in Phase 18 because `.planning/` was preserved as a historical record (D-18).
  Recorded as D-11 with the mapping for the planner; the file was not edited unilaterally.
- **`psutil` 7.2.2 is installed in the dev environment but absent from `pyproject.toml`** —
  the planner must add the extra rather than assume it resolves.
- **SciPy 1.17.0 defaults verified live:** `ftol = xtol = gtol = 1e-8`, `max_nfev = None`.

## Deferred

See `19-CONTEXT.md` § Deferred Ideas.
