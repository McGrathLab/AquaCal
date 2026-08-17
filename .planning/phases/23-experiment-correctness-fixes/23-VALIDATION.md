---
phase: 23
slug: experiment-correctness-fixes
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-08-17
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `23-RESEARCH.md` § Validation Architecture and locked decisions D-07, D-09,
> D-11, D-12.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing `tests/unit/` suite) |
| **Config file** | none dedicated — standard discovery via `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/unit/test_experiments_e1.py tests/unit/test_experiments_e4.py tests/unit/test_experiments_e6.py tests/unit/test_e7_focal_standoff.py tests/unit/test_experiments_provenance.py -x` |
| **Full suite command** | `python -m pytest tests/` — **orchestrator-owned; NOT run by this phase** |
| **Estimated runtime** | quick subset ~60–120 s; cheap-tier runtime probes ~6 min total |

**Interpreter warning:** Git Bash's bare `python` is Anaconda base and produces collection
errors that look like code bugs. Resolve the AquaCal conda env before concluding anything is
broken.

---

## Sampling Rate

- **After every task commit:** the quick run command above, scoped to the touched test files.
- **After every plan merge:** the cheap-tier runtime probes applicable to that plan
  (see Per-Requirement Verification Map).
- **Before `/gsd:verify-work`:** cheap tier green + quick pytest subset green.
- **Max feedback latency:** ~120 s for the unit subset; ~6 min for the full cheap tier.

**Explicitly out of phase (D-11) — do not run, not even "just to be safe":**
E4's nine-cell grid (3.5–4 h), E1's 10-seed band (~1 h), and the unfiltered
`pytest tests/`. Those belong to Phase 28 at the frozen sha.

---

## Per-Requirement Verification Map

Task IDs are populated by the planner; the vehicle and proving value per requirement are fixed
here.

| Requirement | Plan (D-13) | Test Type | Automated Command | Value that proves it | Status |
|---|---|---|---|---|---|
| FIX-01 | 1 | runtime probe | `python -u -m experiments.e1_refractive_comparison --out experiments/verify_23/` | Non-refractive arm's recovered `water_z` reads **1.031 m** (probe measured 1.030999999999). NOT 1.990 m, NOT 0.0120 m. Guard count 0 is corroboration only (D-03), never the test. | ⬜ pending |
| FIX-02 | 1 | runtime probe | same E1 invocation (both arms share it) | Both arms record `normal_fixed: false`; refractive arm's `water_z` stays near its established −7.43 mm offset from 1.031 m rather than making a new large excursion. | ⬜ pending |
| FIX-05 | 2 | unit (`tmp_path`) + read-only `--check` | `python -m pytest tests/unit/test_experiments_e4.py tests/unit/test_experiments_io.py -x` then `python -u -m experiments.e4_benchmark_grid --check` | `build_grid_dataframe` resolves the E2 record relative to the passed `out_dir` at **both** call sites — `_run_check` (`:1876`) and `_run_full` (`:1954`); a non-default `--out` with no native `benchmark.json` yields an announced, explicitly-marked absent row rather than a silent cross-machine import. `--check` exits 0 with `exit_code`/`status_reason` the only skipped columns. | ⬜ pending |
| FIX-03 | 3 | unit | `python -m pytest tests/unit/test_experiments_e6.py -x` | Signed, gauge-corrected Z error column present; per-camera decomposition emitted; both behind the existing collinear caveat; no new verdict column. | ⬜ pending |
| FIX-04 | 3 | unit | `python -m pytest tests/unit/test_e7_focal_standoff.py tests/unit/test_e7_band_mode.py -x` | `fixed` rows carry the vacuous-by-construction label in the existing free-text `scope` column — no schema change, no measured `no_signature` verdict. | ⬜ pending |
| FIX-06 | 4 | inspection | grep the four string sites in `e2_real_rig.py` / `synthetic.py` | Strings read the verified **262 → 52 → 7,762**, not the stale "60 usable frames → 12 validation → 1,817 comparisons". `19.1-E2-FRAMESET-PROVENANCE.md` carries a supersession header rather than an edit. | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Two acceptance traps (from the D-02 probe)

1. **The pin must reach both `build_bounds` import sites** —
   `interface_estimation.py:277` (stage-3 pass 1) and `refinement.py:184` (stage-3 pass 2,
   intrinsic refinement). `_run_one_model` always calls with `refine_intrinsics=True`
   (`e1_refractive_comparison.py:312`), so both run. Patching only pass 1 gives a
   first-pass-only check that *looks* right while `water_z` drifts to 0.0425 m by the end of
   pass 2. A FIX-01 acceptance criterion that reads the first pass only will pass a broken fix.
2. **`optimality_intrinsic` rises when `water_z` is pinned tight** (92.78 vs 49.65 unpinned).
   That is expected numerical behavior of a near-zero-width bound interval, not a conditioning
   regression. The acceptance metric stays the recovered `water_z` (D-03) — never this number.

   > **CORRECTED 2026-08-17 (post-phase). The stated mechanism is wrong; the trap and the
   > acceptance rule are right.** Measured by
   > `.planning/probes/2026-08-17-optimality-decomposition/`: the pinned `water_z` slot
   > contributes **0.00%** of the reported optimality (1.95e-11 of 92.78). scipy's `trf` reports
   > `||g·v||∞` with `v` the Coleman-Li *distance to the bound*, so a pinned parameter is crushed
   > toward zero, not inflated — the reasoning above describes an unscaled projected gradient,
   > which is not the reported quantity. The 92.78 is entirely the max **extrinsic** gradient
   > (extrinsics are unbounded, so `v = 1`). It is a real gradient, not Jacobian noise: a
   > central-difference Jacobian agrees to five significant figures.
   >
   > Also wrong: "not a conditioning regression" is right about *regression* but wrong about
   > *conditioning* — the solve is severely ill-conditioned (directional curvature ~3e8), it is
   > simply not caused by the pin and not new. The solve is **not stalled**; warm restarts
   > recover no cost.
   >
   > **Trap 2 still stands as an acceptance rule** — do not read the number as a pin-induced
   > regression, and keep recovered `water_z` as the metric. Only the explanation changes.

---

## The `--check` Exclusion Contract (D-07 / D-08 / D-09)

`--check` is **not** a verification vehicle for FIX-05. `_run_check`
(`e4_benchmark_grid.py:1836`) hardcodes `"exit_code": None` at `:1872` because no subprocess
runs under `--check`, so the column is always-red by construction.

Named exclusion list — exactly two columns, no heuristic:

- `exit_code`
- `status_reason`

All other 33 of 35 columns reproduce to 1e-6 (measured 2026-08-17). When `--check` is run as a
corroborating step, these two must be the *only* mismatches; anything else is a real regression.

Phase 23 implements the exclusion; Phase 26 (DRIVER-03) documents it. The two must not diverge.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework, fixture, or
harness needs standing up — every requirement has an existing test file or an existing runtime
harness (E1's CLI, E4's `--check` plus `tmp_path` unit fixtures) to extend.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Benchmark record states the held `water_z` value, the mechanism, and the reason (D-04) | FIX-01 | Prose quality — a reader diffing the two arms' records must find both the asymmetry and its justification without leaving the artifact. Not assertable as a string match. | Read the non-refractive arm's benchmark record in `experiments/verify_23/`. Confirm it names the held value (1.031 m), the mechanism (degenerate bounds interval), and the reason (exact null direction at unit index) with a pointer to the measurement. |
| Evidence recorded in each plan's `23-0N-SUMMARY.md` (D-12 as amended 2026-08-17) | FIX-01, FIX-05 | Verification outputs go to a git-ignored `--out` dir and never survive. The transcription is the durable artifact. | Confirm `23-01-SUMMARY.md` gained the recovered `water_z` and the bound-hit table (D-06), and `23-02-SUMMARY.md` the `--check` baseline — as values, not as artifact paths. **No plan may modify `.planning/MANUSCRIPT-FINDINGS.md`**; `git diff --stat` on it must be empty. |
| Always-red gate recorded as a process finding (D-10) | FIX-05 | A knowledge-base prose entry about the pattern, not this instance. | Confirm `.planning/knowledge-base.md` § Known Issues gained an entry on verification gates that cannot pass. |

---

## Output Location (D-12)

Every in-phase verification run writes to `experiments/verify_23/`. Confirm it is git-ignored
(or add it) before the first run. Nothing leaks into the tree Phase 27 packages or that
DRIVER-04 later moves aside. Side effect: this exercises FIX-05's `--out` path for free.

Because those outputs are never committed, **evidence must be transcribed as values, never
referenced as an artifact path.**

**Amended 2026-08-17:** it is transcribed into each plan's own committed `23-0N-SUMMARY.md`, **not**
into `.planning/MANUSCRIPT-FINDINGS.md`. That ledger's charter is measured results citing a
surviving artifact, and this phase runs nothing durable; the findings its fixes correspond to already
exist (MF-12, MF-17, MF-18), the ledger pass is the user's, and the real entries come from Phase 28's
run at the frozen sha. See `23-CONTEXT.md` § Amendment 2026-08-17. Plan 01 additionally closes with a
`### Ledger candidate` note flagging the D-06 bound-hit table for the user.

---

## Validation Sign-Off

- [ ] All tasks have an automated verify or an entry in Manual-Only Verifications
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references *(n/a — none)*
- [ ] No watch-mode flags
- [ ] Feedback latency < 360 s (cheap tier)
- [ ] FIX-01 acceptance reads stage-3 **pass 2** `water_z`, not pass 1 only
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
