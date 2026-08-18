# Probe: solver concurrency and the suite's real runtime

**Date:** 2026-08-18
**Box:** Windows planning box — Intel Alder Lake-H, 14 physical / **20 logical cores**, **15.7 GiB**
(this is the "16 GB Windows box" of `linux32gb_scope.json`)
**Target for comparison:** Linux run machine — i9-13900KF, **32 logical cores, ~31 GiB**
**Vehicle:** one `e1_refractive_comparison` single-seed run (`--force --out <probe>`), exit code 0
**Artifacts:** `probe_cpu_rss.py`, `samples.csv` (157 samples @ 2 s), `summary.json`,
`e1_child.log`. The child's `e1_out/` tree (13 MB, regenerable) was removed after its row counts were verified against the committed artifacts — see Finding 3.

**Why:** the full-suite driver runs stages strictly serially (review H4), a rule written to protect
**timing** measurements. Only `e4`, `e4_repeat`, `e2_timing` and `e2_memory` are timing-sensitive.
If one solve leaves most of the box idle, the accuracy stages could run N-wide.

---

## Finding 1 — a solve uses ~1 core of 20, and never more than 2.6

| statistic | cores busy |
|---|---|
| median | **0.99** |
| mean | 1.20 |
| p95 | 2.01 |
| peak | 2.56 |
| fraction of samples above 1.5 cores | 22% |

Stable across the whole run, Stage 3 (joint refractive optimization) included — see the phase
breakdown in `samples.csv`: t=0–60 s → 1.01 cores, t=60–180 s → 1.25, t=180–316 s → 1.18.

**Mechanism.** No thread limit is set anywhere in `src/` or `experiments/` (`OMP_NUM_THREADS`,
`MKL_NUM_THREADS`, threadpoolctl — all absent), and NumPy 2.4.2 / SciPy 1.17.0 run on
`scipy-openblas`, which defaults to all cores. The solve path densifies the FD Jacobian
(`make_sparse_jacobian_func` → `.toarray()`) so `least_squares` can use `tr_solver='exact'`, which
*is* BLAS-threaded — but at P ≈ 700–1,350 the factorization is small, and the serial Python-level
FD loop (13–17 residual passes per Jacobian) dominates. **~30 of 32 cores sit idle on the target
during every accuracy stage.**

This is a property of the wheels and the problem shape, not the OS, which is why measuring on
Windows settles it for Linux. Worth one confirmation during Phase 27's Linux smoke; not worth
deferring the decision for.

## Finding 2 — memory, not CPU, bounds concurrency; and it was already recorded

E1's peak RSS is **0.61 GiB** — E1 is the suite's smallest solve, so this is a floor, not a guide.
The useful numbers were already in committed `benchmark.json` records and needed no probe. Peak RSS
scales with **frame count**:

| problem size | peak RSS | stages there |
|---|---|---|
| 30 frames | < 1 GiB | E5 (`E5_N_FRAMES = 30`) |
| 100 frames | 2.7–3.5 GiB | **E6 band** (`n_frames = 100` on all 102 rows), E4's 100-frame cells |
| 200 frames | 9.3–11.3 GiB | E2 (10.26 GiB), E4's 200-frame cells |

At ~3.5 GiB for an E6-class band cell, ~7 fit in 31 GiB — far more headroom than the 1-core-per-
solve arithmetic requires.

## Finding 3 — ⚠ two numbers in the 19.4 state file are anomalous, and I had used them

`e1_refractive_comparison` single-seed, measured across three runs of the same stage:

| run | date | wall clock |
|---|---|---|
| 19.3 | 2026-08-02 | 5.7 min |
| **19.4** | 2026-08-05 | **152 min** |
| this probe | 2026-08-18 | **5.3 min** |

The probe's output is complete and correct — `exp1_parameter_errors.csv` (25 rows),
`exp2_depth_generalization.csv` (17), `exp3_xy_vs_z_anisotropy.csv` (17) all match the committed
artifacts exactly. So **19.4's 152 min is the outlier, by ~27×.** `e7` shows the same shape
(5.6 min at 19.3 → 129 min at 19.4).

Every other stage moves by a consistent ~1.6–2.0× between 19.3 and 19.4 — the known machine swing
(`e5` 22 → 45 min, `e6_repeat1` 99.6 → 167, `e4` 132.5 → 214). **`e1` and `e7` do not fit that
pattern.** The likely cause is that 19.4 is the phase that fixed the grid-family clearance floor
(flat NaN clamp + unvalidated `solvePnP`): during that run the geometry was still marginally
conditioned and those two solves ground on. Post-fix they are back to minutes.

**Consequence:** a runtime estimate built on 19.4's `e1`/`e7` rows over-counts badly. Use 19.3 or
this probe for those two stages; 19.4 remains fine for `e5`, `e6`, `e4`.

## Finding 4 — the corrected suite estimate, and what dominates it

At Windows-box speed, with the three grid cuts applied (D-40 scale axis, D-41 noise seeds,
D-42 `e6_repeat2` off):

| stage | estimate | basis |
|---|---|---|
| `e6_band` | **8.9 h** | 10.8 h measured (19.5), less the 18 dropped scale cells |
| `e4` | 2.2–3.6 h | measured, 19.3 / 19.4 |
| `e2` ×4 invocations | ~3.5 h | 48–87 min each |
| `e6_repeat1` | 1.7–2.8 h | measured |
| `e2_band` / `e5_band` | 2.4 / 2.3 h | measured, 19.5 |
| `e1_band` (cut noise plan) | ~2 h | 22 seed-runs × ~5.3 min + overhead |
| `e7_band` | **~1–2 h, UNCERTAIN** | see caveat |
| `e4_repeat` | 1.0 h | measured, 19.5 |
| `e5` / `e1` / `e7` single | ~0.75 / 0.09 / ~0.1 h | measured |
| **serial total** | **≈ 22–26 h** | |

**This replaces the ~50 h figure in `26-CONTEXT.md` § Amendment A**, which used 19.4's anomalous
`e1`/`e7` rows and a loose upper bound for `e7_band`.

⚠ **`e7_band` is the one soft number.** It was bracketed at ≤8.8 h from artifact mtimes, but that
window contained other activity. If E7's single-seed run (4 arms) is ~6–10 min, its 10-seed band
(40 arms) should be ~1–2 h. **Nothing measures this** — no band artifact records its own runtime,
in any CSV or in the `e{N}_seed_band_provenance.json` sidecars. One E7 single-seed run (~10 min)
would settle it.

**`e6_band` is now ~40% of the whole suite and is the critical path under any scheduling.** It is
the highest-value remaining target if more time must be found.

## Finding 5 — concurrency is viable, and its payoff is real but smaller than first thought

Split the queue by whether wall clock is being measured:

- **Serial and alone** (timing-sensitive): `e4`, `e4_repeat`, `e2_timing`, `e2_memory` ≈ **6–7 h**
- **Concurrent, 4–5 wide** (accuracy only, ~16–19 h of work): bounded by the longest single stage,
  `e6_band` at **8.9 h**
- **Total ≈ 15–16 h**, against ≈ 22–26 h serial — a saving of **~8–10 h**, not the ~26 h implied
  by the uncorrected table.

Requires no change to any experiment; only the driver's stage model.

### Three constraints on any concurrent stage model

1. **E6's two stages must never overlap.** `run_stage_e6_repeat1` does
   `rm -rf ${OUT_DIR}/e6_configs` and deletes `generalization_sweep.csv` / `e6_provenance.json`
   under the shared `OUT_DIR`, which `e6_band` also writes.
2. **At most one 200-frame-class stage at a time** (E2, E4's big cells). Five 3.5 GiB stages plus
   one 10.3 GiB stage is 27.8 of 31 GiB — too tight.
3. **Concurrent stages share `experiments/results/`,** so any shared artifact name is a collision.
   The expectation manifest enumerates every artifact anyway, so verifying disjointness is nearly
   free — do it there rather than by inspection.

### Not attempted

Splitting `e6_band` itself across processes by seed. It would attack the critical path directly,
but needs a merge step and provenance handling inside the experiment — out of proportion to a phase
that was just deliberately de-scoped.

---

*Probe run and written 2026-08-18. Nothing under `experiments/results/` was read for output or
modified; the child wrote to this directory via `--out` (Phase 25 D-03 pattern).*
