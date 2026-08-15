---
created: 2026-08-15T00:00:00.000Z
title: DEFERRED — decide whether the production degeneracy gate applies to real-rig runs, and record the answer
area: policy
files:
  - src/aquacal/calibration/_observability.py
  - experiments/e4_benchmark_grid.py
  - experiments/e6_generalization_sweep.py
---

> **DEFERRED until `2026-08-15-classify-the-198-unprojectable-observations.md` reports.**
> Split out of `2026-08-15-narrow-the-degenerate-observation-warning.md` on 2026-08-15, which had
> bundled it with a text fix and sequenced it wrongly. **Not a pre-run item and probably not a
> pre-submission one.**

## Problem

`19.3-07-PLAN.md:120–128` mandates that a PRODUCTION configuration recording
`degenerate_observations_at_solution > 0` gets `status == "degenerate"`, **never `"ok"`**, and is
excluded from every aggregation, table and published summary — explicitly with no threshold and no
fuzz factor. Every synthetic production cell measures 0 and passes.

**The headline real-rig calibration measures 198 and is published as converged.**

The gate does not literally apply, because it is implemented in `e4_benchmark_grid.py` and
`e6_generalization_sweep.py` — the synthetic harnesses — and E2 runs through neither. The
distinction is defensible and probably right: in a synthetic scenario the geometry is *authored*,
so an unprojectable observation means the scenario is malformed and the cell should be discarded;
on a physical rig the geometry is *given*, and a small unprojectable fraction is a fact about the
deployment rather than a construction error.

**But that argument exists nowhere in writing.** A reader of the repository finds a project that
discards synthetic cells at `count > 0` and publishes a real calibration at `count = 198`, with no
sentence reconciling the two.

## Why it is deferred rather than done

The decision depends on a fact nobody has yet: **what the 198 are.** If they are a breached
interface in a handful of frames, "a fact about the deployment" is plainly the right reading and
the gate stays synthetic-only. If they turn out to be something else, the answer may differ. Making
the policy call before the classification lands would be deciding on the strength of the same
assumption the classification exists to test.

The `water_z` pin also changes the landscape: once E1's non-refractive arm reports zero, the real
rig's 198 is the **only** non-zero count in the suite, which makes the question sharper and
narrower than it is today.

## Solution — when it is picked up

Record the answer where the gate lives, not only in a planning file. Either:

- **synthetic-only by design** — state the authored-vs-given-geometry rationale in
  `_observability.py` and in both harnesses' guard blocks, so the next reader meets the reasoning
  at the gate; or
- **extends to real-rig runs** — the production pipeline must then report `status` accordingly,
  which is a larger change and has consequences for how the paper describes its own calibration.

## Do not

- Do not soften the synthetic gate into a threshold. `19.3-07-PLAN.md` is explicit that it stays
  exactly `count > 0 -> degenerate`, with a smoke-path carve-out only.
- Do not action this before the classification. That is the whole reason it is deferred.
- Do not let the deferral quietly become a decision. The gap is real and stays open until written
  down somewhere a code reader will find it.

## Related

- `2026-08-15-classify-the-198-unprojectable-observations.md` — this waits on it.
- `2026-08-15-pin-water-z-in-e1-non-refractive-arm.md` — narrows the question.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, finding F-009b).

## Scope boundary — artifacts, not prose

Library and policy work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only from
this repo.

---

## The 0.268% denominator argument no longer holds (2026-08-15)

This todo's framing — 198 unprojectable of 73,975 observations, "a small unprojectable fraction is
a fact about the deployment" — assumes 198 is a **solution-state count**. It is not.

`run_calibration_from_config` declares `discard_stats: dict[str, int] = {}` once at
`pipeline.py:766` and passes that same object to **six** bump sites (`:808`, `:915`, `:1031`,
`:1107`, `:1280`, `:1439`) with **no reset between stages**, while `_bump` accumulates
(`_observability.py:113`). So the published 198 is a sum over up to six evaluations, and an
observation unprojectable in two stages is counted twice. (Established in
`2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` § "Third defect";
the same pattern was first seen in E1's log, where a reported `1134` is `70` + `1064`.)

**What this does and does not change.**

- It does **not** change the policy question. Whether the synthetic gate should extend to real-rig
  runs is still open and still waits on the classification.
- It **does** invalidate the specific arithmetic this todo leans on. The true count of distinct
  unprojectable observations is ≤ 198 and currently unknown, so "0.268%" is an upper bound of
  unknown tightness, not a measurement. Do not re-quote it until the per-stage split lands.
- It **sharpens** the deferral. The gate cannot sensibly be scoped against a number whose units are
  unclear. The per-stage counter split is now a prerequisite alongside the classification.

**Consequence for the decision when it is picked up:** if the distinct count turns out materially
below 198, the "small fraction is a fact about the deployment" reading gets *stronger*, not weaker.
That is a reason to wait for the number rather than to decide now on the sum.
