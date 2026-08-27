---
created: 2026-08-15T00:00:00.000Z
title: Two scoping probes to run before planning the fix milestone — scratch-only, no committable edits
area: research
files: []
---

## Purpose and hard constraint

Two questions are unanswered whose answers change how the fixes are written. Both are cheap.

> ## ⚠ SCRATCH ONLY — this task produces no committable edits
>
> **Do not modify any tracked file in the AquaCal repo.** No `src/` edits, no experiment-script
> edits, no schema changes, no new committed scripts, no `.planning/` updates, not even a typo fix.
> The probe script and every output go in the scratch directory. The deliverable is a **written
> findings report** handed back in the agent's summary; whether any of it gets persisted is decided
> afterwards.
>
> Two reasons, and the second is the hard one:
> 1. These are measurements taken to *scope* work, not the work.
> 2. **The repo is being edited concurrently** — fix-milestone TODOs are in flight in the same
>    tree. A probe that touches tracked files creates a merge conflict with work in progress.
>
> Verify before finishing: `git status` in the AquaCal repo must show exactly what it showed at
> the start. If it does not, revert the difference and say so in the report.

Environment: conda env `AquaCal` — `C:/Users/tucke/anaconda3/envs/AquaCal/python.exe`. Do **not**
use `uv`.

---

## P1 — E1's noise response

**Runs on the Windows box, which is much slower than the Linux machine the real suite runs on.
Three solves, nothing more. No grid work, no seed sweep, no second arm.**

**Why it gates the milestone.** The decided E1 promotion
(`2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md`) commits the run to four
noise levels × ten seeds. Nothing is known about behaviour above 0.5 px — the scenario has only
ever been run there. If the error scales roughly linearly the conditioned claim writes itself; if
the solve destabilizes at the top level, or starts reporting degenerate observations, the level set
is wrong and the claim has to be rebuilt.

**Recipe.**

1. `scenario = create_scenario("realistic", seed=42)` (`synthetic.py:1005`).
2. **Mutate `scenario.noise_std` before calibrating.** `SyntheticScenario` is a plain `@dataclass`
   (`synthetic.py:35`), not frozen, so assignment works. This is the whole reason no plumbing is
   needed for a probe.
3. `calibrate_synthetic(scenario, n_water=1.333, refine_intrinsics=True, seed=42)` — **refractive
   arm only.**
4. Evaluate at the deepest point only: `_build_dataframes(..., test_depths=[2.5])`. That parameter
   exists (`e1_refractive_comparison.py:374`) and skips seven of eight depths, which is most of the
   evaluation cost.
5. Repeat for `noise_std` ∈ **{0.5, 0.82, 1.2}** px. Add 0.25 px only if three points leave the
   shape ambiguous.

**The non-refractive arm is deliberately excluded.** Its error is model misspecification at the
229 mm scale; sub-pixel detection noise does not move it, and it is not the arm being promoted.

**Self-check that the override actually took effect.** At convergence the refractive arm's
reprojection RMS tracks the injected noise — the committed run reports **0.498 px against 0.5 px
added**. So if the 1.2 px solve comes back with a reprojection RMS near 0.5, the mutation did not
reach detection generation and every other number in the probe is meaningless. Check this first,
before reading any result.

The 0.5 px point should also land near the committed seed-42 value in `exp1_band.csv`. E1 generates
its detections synthetically — no ChArUco detection, no OpenCV version dependence — so a large
discrepancy means the probe is wrong, not the library. **Last-digit platform drift is expected and
uninteresting; do not chase it.**

**Report:** per noise level — 2.5 m Z-RMSE, reprojection RMS, `degenerate_observations_at_solution`,
solver status and optimality. Then one sentence on the shape: linear, super-linear, or unstable.

**Do not** read wall-clock off this machine to scope the Linux run; the timing here is indicative
of nothing.

**Decision it feeds:** keep or revise {0.25, 0.5, 0.82, 1.2}; whether the top anchor is 1.2 px or
lower.

---

## P2 — moved out

Classifying `numbers-ledger.tsv` rows is manuscript-side and belongs to the Spinoffs session, which
owns that tree. **Not part of this task. Do not open the manuscript tree.**

---

## P3 — where 14,907 / 2,128 / 1,134 came from (read-only, time-boxed)

**Why it matters.** The T-14 half of
`2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` is scoped as "add a
column". That is right only if those counts are benign bookkeeping like E1's 14,949. If any is a
genuine geometric failure, it is a finding rather than a schema gap.

**Probe.** Trace the three counts logged in the (now closed)
`done/2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md` back through the 19.4
production-queue logs to the configurations that produced them. For each: which experiment, which
arm, and was the assumed index unity?

**Likely outcome, worth confirming rather than assuming:** if they are all unit-index arms, the
`water_z` pin retires them exactly as it retires E1's 14,949, and T-14 stays a column addition.

**Time-box this.** Those counts survive only in run logs, which may be gitignored or absent from
the tree entirely. If twenty minutes of searching does not locate them, **report that they are
unfindable and stop** — that is itself the answer, and it makes the case for T-14's persisted
column stronger rather than weaker.

---

## P4 — CLOSED 2026-08-15, before this task was written

**Question:** can the 198 be classified offline, from committed artifacts, with no re-run?

**Answer: no.** Checked directly.
`results_e2_band/seed_{42,43,44}/internals/calibration_stage3.json` and
`calibration_stage3_intrinsic_pass.json` carry **cameras only** — `intrinsics`, `extrinsics`,
`water_z`. The 2.2 MB `calibration.json` is 1.26 MB of `diagnostics.per_corner_residuals` /
`per_corner_camera_labels` plus camera parameters; its remaining keys are `metadata`, `board`,
`interface`, `version`. **No per-frame board placements exist in any committed artifact**, the
stage-3 internals included — which the goal-4 audit had not opened.

`2026-08-15-classify-the-198-unprojectable-observations.md` therefore stays run-gated, and its
"do not retry the cheap partial" instruction is now confirmed by a second route. Recorded so nobody
spends the hour a third time. **Nothing to do.**

---

## Do not

- **Do not modify any tracked file.** See the constraint at the top; it is the point of this task.
- **Do not run grid or sweep work on this machine.** If a question seems to need a sweep, it
  belongs in the Linux run, not in a probe.
- Do not let P1 grow into the fix. It is one seed, one arm, one mutated field, three solves; the
  plumbing decision belongs to the milestone.
- Do not shape any finding around preserving a published number. The re-run replaces every
  artifact; numbers move, and understanding why is the deliverable.

## Related

- Feeds `2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` (P1) and
  `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` (P3).

---

## CLOSED 2026-08-15 — all four probes discharged

Ran as `gsd-quick` under the scratch-only constraint. `git status` was byte-identical before and
after; nothing was committed from the probe itself. Full findings report, with raw data and method:
**`Desktop/aquacal-scoping-probes-findings-2026-08-15.md`**.

| probe | outcome | decision it fed |
|---|---|---|
| **P1** — E1's noise response | **Linear.** Z-RMSE/noise flat at 3.875 / 3.792 / 3.826 mm per px; fit R² = 0.99969, max residual 0.027 mm. Zero degenerate observations and `ftol` termination at every level **including 1.2 px**. Anisotropy 2.19–2.29, straddling the published ~2.3. | **Keep `{0.25, 0.5, 0.82, 1.2}`; 1.2 px stands as the top anchor.** No rebuild of the conditioned claim needed. Recorded in `2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md`. |
| **P2** — ledger classification | Moved out of scope 2026-08-15; manuscript-side, owned by the Spinoffs session. The manuscript tree was not opened. | — |
| **P3** — where 14,907 / 2,128 / 1,134 came from | **All five counts are `n_water = 1.0` arms** — E1 single-seed seed 42, and band seeds 42, 44, 48, 50. No refractive-arm occurrence exists in the log. | **T-14 stays a column addition.** The `water_z` pin retires the suite's entire degeneracy population. Recorded in `2026-08-15-pin-water-z-in-e1-non-refractive-arm.md`. |
| **P4** — classify the 198 offline | Closed before the task began: no committed artifact holds per-frame board placements. | `classify-the-198` stays run-gated. |

**Two findings the probes were not asked for**, both filed rather than left in the report:

- `degenerate_observations_at_solution` **accumulates across stages** — absorbed and extended into
  `…-merges-two-failure-kinds.md`, which found the production path passes one dict to **six** bump
  sites with no reset.
- **Beyond-critical-angle obliquity is not a trigger.** No TIR check exists in the projection path
  (`refract_ray` has zero callers), and zero unprojectable corners were measured on both presets at
  ground truth. Filed as
  `2026-08-15-degeneracy-instrumentation-the-rerun-must-emit.md` Finding 3.

**Validity note worth carrying forward:** P1 ran through `_run_one_model`, which passes no
`normal_fixed` and therefore inherited the library default `True`. Its exact reproduction of the
committed seed-42 anchor confirms the harness against the **current** default — not against the
`normal_fixed=False` the re-run will use.
