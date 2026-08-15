---
created: 2026-08-15T00:00:00.000Z
title: normal_fixed was unified to False at the config layer only — E1 and E7 enter the library directly and inherit True, so they solve a problem two DOF smaller than the production pipeline
area: experiments
resolves_phase: 23
files:
  - experiments/e1_refractive_comparison.py
  - experiments/e7_interface_ablation.py
  - src/aquacal/datasets/pipelines.py
---

## Problem

The interface-tilt default was unified to "tilt free" at the **config** layer and nowhere else.

- `CalibrationConfig.interface_normal_fixed: bool = False` (`config/schema.py:333`) — tilt **on**.
- Every library signature still defaults `normal_fixed: bool = True` — tilt **off**. Eighteen of
  them, across `_observability.py`, `_optim_common.py`, `interface_estimation.py`,
  `point_refinement.py`, `refinement.py`, and `calibrate_synthetic` (`datasets/pipelines.py:36`).

So what a caller gets depends on how it enters the library, and the suite is split:

| experiment | entry point | resolved `normal_fixed` | tilt |
|---|---|---|---|
| E2 (production) | `run_calibration_from_config` → config default | `False` | free |
| E3 | `SCALING_NORMAL_FIXED = False`, passed explicitly | `False` | free |
| E4 | `GRID_NORMAL_FIXED = False`, passed explicitly | `False` | free |
| E5 | `E5_NORMAL_FIXED = False`, passed explicitly | `False` | free |
| E6 | `GRID_NORMAL_FIXED`, passed explicitly | `False` | free |
| **E1** | `calibrate_synthetic` — **no `normal_fixed` anywhere in the file** | `True` | **fixed** |
| **E7** | `optimize_interface` / `joint_refinement` **directly** — none passed | `True` | **fixed** |

`e4_benchmark_grid.py:155` already records the hazard in a comment — *"optimize_interface and
joint_refinement both default normal_fixed=True, so this MUST be passed explicitly at every call
site — omitting it silently solves a problem two tilt DOF smaller."* E4, E5 and E6 heeded it.
E1 and E7 do not pass it.

**This was never checked by the goal-4 audit.** V-006 verified E4's explicit `False` and concluded
the config-default flip "cannot reach this experiment" — true of E4, and never tested against E1 or
E7. A concrete instance of the audit's own coverage-enumeration gap.

## Why it matters, and why the two cases differ

**E1 — the numbers are from an easier problem than the shipped default solves.** Nothing is
*mis-specified*: the synthetic scenario's ground-truth interface really is flat and axis-aligned
(`generate_real_rig_array`, frozen `WATER_Z`), so fixing the normal hands the solver correct
information. But E1 produces the abstract's headline accuracy figures, and a user running AquaCal's
own default estimates two parameters E1 did not. That bears directly on the absolute-accuracy
licensing decision recorded in `REVISION-ROADMAP.md` §10.8.

**E7 — flipping it may change the result, not just the digits.** E7 is the *interface* ablation.
With the normal locked it compares shared versus per-camera **standoff**, not full interface
geometry, while supplement §14's claim is about the interface parameterization. The 10-of-10
fixed-intrinsics sign test is exactly the kind of result that may not survive two extra free
parameters per interface. **Treat E7 as a decision, not an automatic fix.**

## DECIDED 2026-08-15 — every experiment runs `normal_fixed=False`

**Author's reasoning, which is stronger than the consistency argument and should be the one
recorded:** fixing the normal to `[0, 0, -1]` asserts that the reference camera's optical axis is
exactly perpendicular to the water surface. That is a claim about how well the rig was mounted, not
a property of the physics, and no deployment gets it for free. It is unfair to assume it.

It also moves the accuracy numbers in the conservative direction: estimating two parameters that
happen to sit at their true values is strictly harder than being handed them, so what the suite
reports is what a user actually faces.

- **E1: pass `normal_fixed=False`.** Its numbers will move; expected and fine.
- **E7: pass `normal_fixed=False`** — decided, superseding this todo's earlier
  "check the design intent first". Still **check MF-05 and the 19.2/19.5 plans for a recorded
  rationale**, not to reverse the decision but so that if one exists it is answered rather than
  silently overridden.

**Precision worth keeping on record.** The synthetic scenarios generate the interface at exactly
`[0, 0, -1]`, so running tilt-free measures **the cost of having to estimate a tilt you do not
need** — it does *not* demonstrate recovery of a real tilt. That would require scenarios generated
with a non-zero interface tilt, which is a different experiment and is **not** in scope for this
run. Do not let the two claims blur in any artifact description.

**Consequence to watch for specifically: E7's ablation result may change.** The fixed-intrinsics
arm currently wins 10 of 10 seeds with no zero crossing, p = 0.00098 (supplement §14). Two extra
free parameters per interface is exactly the kind of change that could soften a 10/10. If it does,
the new number is the honest one — but flag it explicitly in the post-run report rather than
letting it surface during re-verification, because it is a published result moving.

**Bonus, worth telling the manuscript session:** with this change the *whole* suite runs
tilt-enabled, matching the production pipeline. The supplement can then describe one setting for
everything instead of qualifying per experiment.
## Solution

- **Pass `normal_fixed=False` at E1's and E7's call sites.** E1 enters via `calibrate_synthetic`;
  E7 calls `optimize_interface` / `joint_refinement` directly. Both currently pass nothing.
- **Add a test asserting every experiment passes `normal_fixed` explicitly.** This is the pre-run
  half of closing the trap, and it is the part that actually prevents recurrence — E1 and E7 were
  not wrong on purpose, they simply omitted an argument. A test makes omission loud. Cheap, touches
  no shared code path.
- **The source-level reconciliation is DEFERRED to post-submission** —
  `2026-08-15-POST-SUBMISSION-reconcile-normal-fixed-defaults-between-config-and-library.md`.
  Decided 2026-08-15: `point_refinement.py` holds six of the eighteen `True` defaults and is the
  AquaPose bridge, so a global flip reaches a second library days before a deadline, on a path this
  milestone has no coverage over. **Do not flip library defaults in this milestone.**
- **Record the resolved `normal_fixed` in E1's and E7's provenance records** the way E4/E5/E6
  already do — it is currently unrecoverable from their artifacts.
- **Register the changed artifacts with the suite driver and its completeness gate**
  (`2026-08-15-make-the-suite-driver-cover-every-invocation.md`). E1's and E7's provenance records
  gain a field and E7's band values may move; the expectation sheet
  (`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`) must know both.

## Do not

- ~~Do not flip E7 without checking the design intent.~~ **Superseded by the DECIDED section above,
  2026-08-15: E7 passes `normal_fixed=False`.** What survives of this caution: still check MF-05
  and the 19.2/19.5 plans for a recorded rationale, so that if one exists it is *answered* rather
  than silently overridden — and flag the movement explicitly in the post-run report, because
  E7's 10-of-10 fixed-intrinsics result is published in supplement §14.
- Do not flip the library defaults as a quick fix without auditing every caller. Eighteen signatures
  default `True`, including `point_refinement.py`'s six, which serve the downstream
  AquaPose bridge — a silent two-DOF change there reaches another library.
- Do not treat E1's fixed normal as a bug in its results. The scenario's interface *is* flat; the
  solve is correct for the problem posed. The issue is that the problem posed is not the one the
  shipped default poses.

## Related

- Audit V-006 (`Spinoffs/papers/aquacal/AUDIT-goal4.md`) — verified E4 only.
- `REVISION-ROADMAP.md` §10.8 — the E1 absolute-accuracy decision this bears on.
- `2026-08-15-make-the-suite-driver-cover-every-invocation.md` — the resolved value belongs in the
  per-invocation record.

## Scope boundary — artifacts, not prose

Library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only
from this repo. If E7's result moves, report the new numbers; do not edit the supplement.
