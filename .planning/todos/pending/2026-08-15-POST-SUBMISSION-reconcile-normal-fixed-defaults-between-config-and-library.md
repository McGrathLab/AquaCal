---
created: 2026-08-15T00:00:00.000Z
title: POST-SUBMISSION — normal_fixed defaults disagree between the config layer (False) and eighteen library signatures (True); reconcile them at the source
area: library
files:
  - src/aquacal/config/schema.py
  - src/aquacal/datasets/pipelines.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/calibration/point_refinement.py
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/calibration/_observability.py
---

> # ⏸ DEFERRED — POST-SUBMISSION. Do NOT action in the fix milestone.
>
> **Decided 2026-08-15.** The experiment-level fix lands pre-run
> (`2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else.md`); this
> source-level reconciliation waits until after the SoftwareX submission. Revisit against a suite
> that is no longer the paper's evidence.

## Problem

`normal_fixed` resolves differently depending on which documented entry point a caller uses:

- `CalibrationConfig.interface_normal_fixed: bool = False` (`config/schema.py:333`) — tilt **free**.
  This is what the production pipeline, the CLI, and E2 get.
- `normal_fixed: bool = True` in **eighteen** library signatures — tilt **fixed**. This is what any
  direct caller gets: `_observability.py` (×3), `_optim_common.py` (×6),
  `interface_estimation.py`, `refinement.py`, `point_refinement.py` (×6), and
  `calibrate_synthetic` (`datasets/pipelines.py:36`).

**A default that differs between the two documented ways into the library is the defect.** It has
already cost real work: E1 and E7 silently solved a problem two tilt DOF smaller than the
production pipeline for the entire life of the manuscript, and the goal-4 audit did not catch it
because V-006 checked only E4 — which passes `False` explicitly and so is immune.

`e4_benchmark_grid.py:155` documents the hazard in a code comment rather than fixing it: *"…this
MUST be passed explicitly at every call site — omitting it silently solves a problem two tilt DOF
smaller."* A comment is not a mechanism.

## Why it is deferred rather than fixed now

**`point_refinement.py` holds six of the eighteen defaults, and it is the AquaPose bridge.** A
global flip is not a `sed` — it changes behaviour in a second library, days before a deadline, on a
code path this milestone has no coverage over. The risk is asymmetric: the failure mode being
guarded against (an experiment inheriting the wrong default) is fully mitigated pre-run by passing
`False` explicitly everywhere plus a test that asserts it, and that mitigation touches nothing
shared.

## Solution — when it is picked up

Two coherent options. Decide, do not drift.

**(a) Flip the library defaults to `False`**, matching the config layer, so both entry points agree.
The real fix, and the one that removes the trap permanently. Requires a caller audit rather than a
find-and-replace:

- Every call site in `src/`, `experiments/`, and `tests/`.
- **`point_refinement.py` needs its own judgement, not the blanket answer.** Its functions refine
  point correspondences against an already-solved calibration, where the interface normal is
  typically a *recovered* quantity being held — so `True` may be semantically correct there even
  after the rest flip. Read the intent before changing it; a wrong flip here reaches AquaPose.
- The downstream AquaPose bridge (`refine_calibration()`) must be checked against whatever is
  decided, and the change communicated rather than assumed inert.

**(b) Keep `True` and make omission impossible** — retain the defaults, but add a test asserting
every experiment passes `normal_fixed` explicitly, and consider making the parameter
keyword-only-without-default in the internal entry points so omission is a `TypeError` rather than
a silent two-DOF change. Safer for existing callers, but it leaves the two entry points disagreeing
and relies on discipline at every future call site.

**Recommendation: (a), with `point_refinement.py` decided on its own merits.** The whole reason this
todo exists is that discipline failed silently twice.

## Do not

- **Do not action this in the fix milestone.** The pre-run mitigation is sufficient and this is not.
- Do not `sed` the eighteen signatures. Six of them serve another library.
- Do not flip and assume inertness. A two-DOF change to a solve is exactly the class of change that
  "cannot move committed results" arguments have been wrong about before (cf. commit `7e0cb90`'s
  scoping error, audit F-005).
- Do not close this by adding another code comment. `e4_benchmark_grid.py:155` already tried that.

## Related

- `2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else.md` — the
  pre-run experiment-level fix, and the finding that surfaced this.
- Audit V-006 (`Spinoffs/papers/aquacal/AUDIT-goal4.md`) — verified E4 only; an instance of the
  audit's own coverage-enumeration gap.
- `2026-07-23-reduce-memory-and-cpu-load-during-calibration.md` — the other item deliberately held
  until after submission, for the same reason: it touches the path every experiment routes through.

## Scope boundary — artifacts, not prose

Library work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only from this repo.
