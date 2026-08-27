---
created: 2026-08-17T00:00:00.000Z
title: POST-SUBMISSION — water_z's [0.01, 2.0] m optimization bound is a bare literal, so any rig with a standoff over 2 m must fork the library
area: library
files:
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/calibration/interface_estimation.py
  - docs/guide/troubleshooting.md
  - docs/guide/optimizer.md
---

## Problem

`_optim_common.py:571-575` bounds the `water_z` parameter with two hardcoded literals:

```python
# Water surface Z bound: [0.01, 2.0] meters. In per-camera mode every one of
# the N water_z parameters gets the same bound.
water_z_idx = n_tilt_params + n_extrinsic_params
lower[water_z_idx : water_z_idx + n_water_z_params] = 0.01
upper[water_z_idx : water_z_idx + n_water_z_params] = 2.0
```

`build_bounds` takes seven arguments and none of them is a bound. There is no config key, no
CLI flag, and no keyword. The documentation states the consequence plainly —
`docs/guide/troubleshooting.md:99`: *"If your cameras are farther than 2m from the water surface,
you'll need to modify the bounds in the source code."*

**This contradicts the library's stated posture.** AquaCal is presented as a general refractive
calibration library for arbitrary multi-camera arrays; a user whose rig sits 3 m above the surface
cannot calibrate without editing installed source. That is a hardware assumption baked into a
solver, and it is the same class of defect as the camera-agnosticism rule already recorded for
validation checks (checks must derive from input data, not assumed hardware).

**The library already has the correct pattern in the same function.** Intrinsics bounds at
`:588-591` are *relative to the data* — `0.5 * fx` to `2.0 * fx` — and scale to any camera. So this
is not a design philosophy applied consistently; it is two of five bound slots that never got
converted. The tilt bound (`±0.2` rad, ~11°, at `:566-569`) is the other absolute one and has the
same question hanging over it, though it is far less likely to bind in practice.

## Evidence that the bound actually binds

Measured 2026-08-17 while probing E1 (`.planning/probes/2026-08-17-phase-23-recon/`):

| E1 arm | recovered `water_z` | where |
|---|---|---|
| n=1.0, `normal_fixed=True` | **1.990 m** | against the 2.0 upper bound |
| n=1.0, `normal_fixed=False` | **0.0120 m** | against the 0.01 lower bound |
| n=1.333, `normal_fixed=False` | 1.0236 m | interior |

Both degenerate arms terminate *on a bound* rather than at a minimum. That is a separate finding
about the unit-index null direction (it belongs to FIX-01), but it demonstrates the box is not
merely decorative — solutions do reach it, and when they do the reported value is an artifact of a
hardcoded constant rather than of the data.

## Solution sketch

- Add a `water_z_bounds: tuple[float, float] | None = None` parameter to `build_bounds`, threaded
  through `optimize_interface` and the config layer, **defaulting to today's `(0.01, 2.0)`** so
  every existing number is bit-unchanged.
- Then, as a separate decision: consider deriving the default from the input data — camera Z
  positions and the initial `water_z` estimate bracket a plausible range without any constant.
  **Keep this as a second step.** Moving the feasible region changes every solve, and doing it in
  the same change as the parameterization makes a bit-identity check impossible.
- Correct `docs/guide/troubleshooting.md:99` and `docs/guide/optimizer.md:131,163` once the
  limitation is actually gone. **Do not "fix" the docs first** — they currently describe a real
  limitation accurately, and rewriting them before the code would make them false.

## Sequencing — deliberately deferred (author, 2026-08-17)

Raised during `/gsd-discuss-phase 23` and **explicitly deferred to post-submission**. The
2026-08-21 SoftwareX deadline is six days out and Phase 27 freezes one sha for the full re-run; the
milestone's posture is a minimal pre-freeze diff.

It was a genuine judgment call, and the reasoning is worth keeping. Under the milestone's scope
test — *does it change what the suite measures, records, or can claim?* — this fails on the suite
but arguably passes on the library: no production solve lands on the bound (the real rig's
`water_z` is ~1.0738 m against camera heights 1.047–1.113 m), and the two solves that do hit it are
the degenerate E1 arms that FIX-01 pins regardless. So no published number moves. What it changes
is what the *library* can claim about generality, in the milestone whose output is a paper
describing that library. The author's call was that a reviewer is more likely to punish a
late-breaking solver change than a documented bound.

**Consequence for FIX-01:** the pin is threaded as its own narrow change rather than riding on a
general `water_z_bounds` parameter. If this todo lands later, FIX-01's mechanism should be
refactored to use it — the two are the same threading done twice.

## Do not

- Do not widen the bound to some larger constant. That relocates the problem instead of removing
  it, and a wider box makes the degenerate arms wander further before stopping.
- Do not change the default numerically in the same change that parameterizes it. Bit-identity
  against the committed suite is the only cheap proof that the threading is inert.
- Do not touch this before the frozen re-run. Every experiment routes through `build_bounds`.

## Related

- `2026-08-15-POST-SUBMISSION-reconcile-normal-fixed-defaults-between-config-and-library.md` — same
  shape (a solver-level default that disagrees with the library's public posture), same deferral
  reason, same file. Do them together.
- `2026-08-15-pin-water-z-in-e1-non-refractive-arm.md` — FIX-01, which pins `water_z` in E1's
  non-refractive arm and would consume this parameter if it existed.
- `.planning/phases/23-experiment-correctness-fixes/23-CONTEXT.md` — D-05, where the deferral was
  decided.

## Scope boundary — artifacts, not prose

Library and docs work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only from this
repo.
