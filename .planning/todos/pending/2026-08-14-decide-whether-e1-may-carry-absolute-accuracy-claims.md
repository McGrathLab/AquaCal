---
created: 2026-08-14T00:00:00.000Z
title: Add a noise_std axis to E1's seed band, so its absolute accuracy numbers carry a stated domain
area: experiments
resolves_phase: 25
files:
  - experiments/e1_refractive_comparison.py
  - src/aquacal/datasets/synthetic.py
  - .planning/MANUSCRIPT-FINDINGS.md
---

## Decision — settled 2026-08-15, implement as scoped

**E1 is promoted to carry absolute accuracy claims, conditioned on a measured noise axis.** The
geometry axis considered alongside it (`n_cameras ∈ {8, 12, 16}`) is **explicitly skipped**.

The reasoning is manuscript-side and lives in **`REVISION-ROADMAP.md` §10.8** (Spinoffs repo) —
why D-19.3-17's demotion never bound this question, and the licensing division it rests on. Two
sentences of it matter here, because they constrain the implementation:

- The absolute number currently measures **estimator variance under a perfectly specified model at
  an asserted \SI{0.5}{px} noise level**. `calibrate_synthetic` generates detections at the
  scenario's `n_water = 1.333` and hands the calibration a *separate* assumed index, so the
  refractive arm is generated and inverted by the same forward model. Nothing justifies 0.5 px, and
  the production rig measures **0.82 px**.
- **E1 bounds estimator variance under stated noise; E2 carries the accuracy claim against
  reality.** Model mismatch is absent from E1 by construction and is not what this axis measures.

Record the decision in `e1_refractive_comparison.py`'s header beside the existing demotion note, so
the next reader meets both halves and the tension does not resurface.

## Scope for the re-run

- **Add a `noise_std` axis to E1's band.** Run the depth sweep at four levels — **0.25 / 0.5 / 0.82 /
  1.2 px** — across the existing ten seeds. 0.82 px is the rig's measured value and is the level that
  makes the claim transferable; 0.5 px must stay in the set because it reproduces the committed
  baseline and E1's D-19 reproduction bar.
- **Schema:** `exp1_band.csv` gains a `noise_std` column. This is precedented — D-19.4-14 already
  gained columns on that artifact rather than adding a sibling file. Row count goes 160 → 640.
- **Plumbing:** `create_scenario` (`synthetic.py:1005`) takes no noise parameter, so the level has to
  be threaded — either a new argument or an explicit override of `scenario.noise_std` before the
  solve. Overriding the scenario field is sufficient and gets the evaluation set for free:
  `e1_refractive_comparison.py:438` already passes `scenario.noise_std` when generating test-set
  detections, so calibration and evaluation noise track together, which is what a rig-level claim
  needs.
- **Cost:** 40 solves where there are now 10. E1 is 12 cameras × 30 frames, the cheapest solve in the
  suite.

**Shape check before committing to the level set:** `2026-08-15-scoping-probes-before-the-fix-milestone.md`
P1 runs three solves at 0.5 / 0.82 / 1.2 px on one seed. If the top level destabilizes the solve or
produces degenerate observations, revise the levels before the milestone rather than during it.

## Do not

- **Do not drop 0.5 px from the noise set.** It is the level every committed E1 artifact was
  measured at and the level E1's `--check` reproduction bar compares against; losing it makes the
  new band incomparable to the old one.
- **Do not change the headers of `exp1_parameter_errors.csv`,
  `exp2_depth_generalization.csv` or `exp3_xy_vs_z_anisotropy.csv`.** Those are fixed contracts
  under D-19, read byte-for-byte by the external figures repository. Only `exp1_band.csv` gains a
  column.
- **Do not add the geometry axis.** Considered and deliberately skipped 2026-08-15; the absolute
  claim is conditioned on the stated 12-camera / 30-frame scenario instead of generalized across
  geometries.
- Do not edit the manuscript. The reconciliation this TODO owns lives in the experiment script's
  header, beside the demotion note. The corresponding prose change is the manuscript session's.
- Do not silently drop the demotion note to make the conflict disappear. It records a real gate;
  what changed is that the gate was found not to govern this question.

## Related

- **`REVISION-ROADMAP.md` §10.8** (Spinoffs) — the decision, its rationale, and the manuscript
  consequence. Read that before changing anything here.
- `.planning/MANUSCRIPT-FINDINGS.md`, "The independent tension this measurement does NOT
  resolve" — the fullest statement of the original problem, and the source of the MF-08/MF-16 line.
- `.planning/todos/done/2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md` —
  **closed 2026-08-15**; carried the adjacent question of whether the `n_water = 1.0` arm is
  converged, answered YES by MF-18.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, finding F-012, TODO ledger T-13).

## Scope boundary — artifacts, not prose

This TODO is library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/` —
`main.tex`, `supplement.tex`, `response-letter.md`, `numbers-ledger.tsv`) is **read-only from this
repo and must not be edited here**, including "obviously correct" single-number updates.

Where a fix has a manuscript consequence, the deliverable is the **evidence, not the sentence**:
emit the artifact, and record the derivation in `.planning/MANUSCRIPT-FINDINGS.md`. Incorporating
it into the paper — prose, ledger rows, captions, figure captions — happens in the manuscript
session, which owns that tree and the word budget.

References to `main.tex` / `supplement.tex` line numbers anywhere in this file are **motivation and
provenance**, never work orders.

---

## Re-run scoping question ANSWERED (P1 probe, 2026-08-15)

This todo notes that resolution (c) — promote E1 by giving it E7-style seed-band backing — is
"a re-run scoping decision… scope it into the full suite now if this is the choice", and that
nothing was known about E1's behaviour above 0.5 px. That gap is now closed by measurement.

**Three solves, refractive arm, seed 42, deepest test point (2.5 m), `noise_std` ∈ {0.5, 0.82, 1.2}:**

| noise px | reproj RMS | Z-RMSE @2.5 m | anisotropy | degenerate obs | stage 3 | intrinsic pass |
|---|---|---|---|---|---|---|
| 0.5  | 0.49904 | 1.9376 mm | 2.193 | **0** | ftol | ftol |
| 0.82 | 0.81865 | 3.1098 mm | 2.258 | **0** | ftol | ftol |
| 1.2  | 1.19849 | 4.5907 mm | 2.293 | **0** | ftol | ftol |

**The response is linear.** Z-RMSE/noise = 3.875 / 3.792 / 3.826 mm per px — flat over a 2.4× range.
Fit `z = 3.7934·noise + 0.0262`, **R² = 0.99969**, max residual 0.027 mm; through-origin slope
3.8214 mm/px fits as well, so there is no meaningful intercept.

**Nothing destabilizes at the top level.** All six solves terminated on `ftol`, and
`degenerate_observations_at_solution` is **0 at every level including 1.2 px**. The anisotropy ratio
stays 2.19–2.29, straddling the published ~2.3, so that claim survives the range rather than
breaking at the top.

**Decision: keep the level set `{0.25, 0.5, 0.82, 1.2}` unchanged, and keep 1.2 px as the top
anchor.** No rebuild of the conditioned claim is needed. If anything 1.2 px is conservative — the
curve had not begun to bend and the solver had not started straining.

**Validity, both checked before the numbers were read:** reprojection RMS tracks injected noise at
all three levels (so the `scenario.noise_std` override reached detection generation), and the 0.5 px
point reproduces the committed seed-42 anchor **exactly** — `z_rmse_mm = 1.9375999763160514` against
a committed 1.9376.

**What this does NOT establish.** One seed, one arm, three points. It fixes the *shape* as linear
and shows the solve is healthy across the range; it gives the slope no seed band. Under D-19.3-17
this confers no accuracy claim by itself — the ten-seed run is still what would back resolution (c).

Full data and method: `Desktop/aquacal-scoping-probes-findings-2026-08-15.md` §1.

---

## ⚠ Collides with the `normal_fixed` change — the 0.5 px rationale is void (2026-08-15)

**Read `2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else.md` before
implementing this todo.** It decides that E1 passes `normal_fixed=False`, where it currently
inherits the library default `True`. Both todos change E1's band in the same run and neither
originally referenced the other.

**The consequence is specific.** The "Do not" above says to keep 0.5 px in the noise set *because*
"it is the level every committed E1 artifact was measured at and the level E1's `--check`
reproduction bar compares against; losing it makes the new band incomparable to the old one."
**With the interface normal freed, 0.5 px will no longer reproduce the committed baseline** — E1
will be solving a problem two DOF larger, and that todo says plainly its numbers will move.

So:

- **Keep 0.5 px, but for a different reason.** Not baseline reproduction — that is gone either
  way. Keep it because it anchors the new band to the level the whole prior literature of this
  project was measured at, so the *change* attributable to freeing the normal is readable at a
  familiar operating point.
- **Do not attempt to preserve E1's `--check` reproduction bar across this run.** It cannot
  survive, and trying to make it pass is exactly the mid-run baseline repair
  `2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` warns against. E1's band is
  already in that todo's suspend list for the `noise_std` column; the `normal_fixed` change means
  E1's *single-seed* artifacts move too, which that todo does not yet account for.
- **Expect a two-factor movement and attribute it.** The new band differs from the committed one
  by both the added noise levels and the freed normal. At 0.5 px the noise axis contributes
  nothing, so the 0.5 px row isolates the `normal_fixed` effect cleanly — worth reporting as such
  rather than presenting one blended delta.

**Also note for the scoping probe's numbers:** P1's three solves ran through `_run_one_model`,
which passes no `normal_fixed` and so inherited `True`. Its exact reproduction of the committed
seed-42 anchor validates the harness against the **current** default. The linear shape it measured
is a property of the noise response and is not expected to change; the absolute values will.

## Register the outputs with the driver and the gate (added 2026-08-15)

**Last step of this fix, not an afterthought.**
`2026-08-15-make-the-suite-driver-cover-every-invocation.md` requires that every schema- or
value-changing fix add its outputs to the suite driver's stage list and to the completeness gate's
expected-artifact list, and asks each such todo to say so. This is that clause — it was missing
from every one of them until now, which is exactly the unenforced coupling that todo warned about.

For this fix specifically: `exp1_band.csv` gains a `noise_std` column and its row count goes 160 -> 640 (10 seeds x 4 noise levels x depths x models). The gate must assert the new count, or a run that silently drops a noise level still passes.

Also add the same expectations to the sheet in
`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`, since hand-verification is the
only check covering these artifacts during this run.

---

## Overtaken by ruling A1 — annotation only, 2026-08-24 (Phase 29.1, plan 03)

**Stays pending.** The accuracy-claim decision this todo owns belongs to Phase 25/29, not to Phase
29.1, and nothing here is being decided. What follows corrects the *plan* this file describes,
because a reader arriving today would implement a grid that was cut nine days ago.

**Ruling A1 (2026-08-15, recorded at `run_experiment_suite.sh`'s `run_stage_e1_band`) resized the
seed axis from ten to four.** The scoping text above still describes the ten-seed plan
throughout:

- § *Scope for the re-run* — *"across the existing ten seeds"* and *"Row count goes 160 → 640"*.
  Under ruling A1 the band is **four** seeds and the emitted CSVs are **256 rows** of
  `exp1_band.csv` and **384 rows** of `exp1_parameter_band.csv` (`4 seeds × 4 noise levels × 16` and
  `× 24` rows per cell). Both counts are confirmed against the committed 2026-08-20 output.
- § *Cost* — *"40 solves where there are now 10"*. Under ruling A1 it is 16 of those 40 cells,
  sized at about 2.8 h against the ten-seed plan's ~7 h. That cost is why the axis was cut.
- § *Register the outputs with the driver and the gate* — *"row count goes 160 -> 640 (10 seeds x 4
  noise levels x depths x models). The gate must assert the new count."* The gate does assert a
  count; it asserts the **four**-seed one, via `suite_expectations.json`'s `full` profile.
- § *Re-run scoping question ANSWERED* — its P1 probe results and the linear-response finding are
  **unaffected**: they are one-seed measurements of the noise response, and ruling A1 changed only
  the seed axis. The level set `{0.25, 0.5, 0.82, 1.2}` it locks is unchanged and was executed.

**What was implemented, and where the record is.** The `noise_std` axis landed and the band ran in
the 2026-08-20 production suite. Phase 29.1 plan 02 then made the band's `scope` field **derived at
write time** rather than a literal, precisely because a corrected literal buys one grid resize
before it rots again (D-08/D-10) — so `e1_seed_band_provenance.json` now states the seed list, both
emitted row counts, the noise levels and the depths of the run that wrote it. Plan 03's bounded
stale-string sweep then found and corrected **six further sites** in
`e1_refractive_comparison.py` and one in `run_experiment_suite.sh` that still stated this todo's
ten-seed arithmetic; see
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-STALE-STRING-AUDIT.md`.

**Do not** update the numbers in the body above. They record what was planned on 2026-08-14, and
this section records what ruling A1 changed — the same retain-and-attribute treatment the rest of
this class gets. Read the two together.

**Why this stays pending.** The question this todo actually owns — whether E1 may carry absolute
accuracy claims, and the header reconciliation with D-19.3-17's demotion note — is a Phase 25/29
scope decision resting on `REVISION-ROADMAP.md` §10.8 in the Spinoffs repo. Phase 29.1 changes what
the suite records about itself and never what it claims, so it is the wrong phase to settle it in.
