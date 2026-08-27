"""SCRATCH PROBE — D-02: does pinning water_z (FIX-01) interact with normal_fixed=False (FIX-02)
in E1's non-refractive arm?

Mirrors e1_refractive_comparison._run_one_model exactly, with a single arm:
  n=1.0 (non-refractive), water_z PINNED to 1.031 m via a degenerate bounds interval
  (lb = ub +/- 1e-12), normal_fixed=False (FIX-02's DOF).

Mechanism (probe-only, NOT production): monkeypatches
`aquacal.calibration.interface_estimation.build_bounds` -- the name bound inside
`optimize_interface`'s module namespace via `from aquacal.calibration._optim_common import
(build_bounds, ...)` at interface_estimation.py:20. The wrapper calls the real build_bounds
for every slot, then overwrites the water_z slot's [lower, upper] pair with a degenerate
interval. This is NOT a faithful stand-in for D-01's planned production threading (a bounds
override kwarg reaching build_bounds from the experiment / calibrate_synthetic) -- it patches
the function object site-wide for the process, which is fine for a single-arm probe but must
not be copied into src/. See D-01: the production pin threads a bounds override parameter,
it does not monkeypatch the library.

water_z slot index derivation (shared_interface=True, the E1 default), from
_optim_common.py:550-575:
    n_tilt_params      = 0 if normal_fixed else 2   -> 2 (normal_fixed=False)
    n_extrinsic_params = 6 * (n_cams - 1)
    water_z_idx         = n_tilt_params + n_extrinsic_params
    n_water_z_params     = 1 (shared_interface=True)

Writes ONLY to the scratchpad-adjacent probe dir. Touches no tracked file.

Baseline for comparison (already measured, in probe_normal_fixed.json -- NOT re-run here):
  n=1.0, normal_fixed=False, water_z UNPINNED -> water_z=0.011959561136834829 m,
      cost_interface=26067.020584816863, degenerate_observations_at_solution=0,
      status_interface=2 (bound-constrained convergence per scipy least_squares docs)
"""

import json
import sys
import time
import traceback
from pathlib import Path

from aquacal.calibration import _optim_common
from aquacal.calibration import interface_estimation as ie_mod
from aquacal.calibration import refinement as ref_mod
from aquacal.calibration._observability import SolverDiagnostics
from aquacal.datasets import calibrate_synthetic, create_scenario

OUT = Path(sys.argv[1])
SEED = 42
PINNED_WATER_Z = 1.031
PIN_HALF_WIDTH = 1e-12

_real_build_bounds = _optim_common.build_bounds


def _pinned_build_bounds(camera_order, frame_order, reference_camera, *args, **kwargs):
    lower, upper = _real_build_bounds(
        camera_order, frame_order, reference_camera, *args, **kwargs
    )
    normal_fixed = kwargs.get("normal_fixed", True)
    n_tilt_params = 0 if normal_fixed else 2
    n_extrinsic_params = 6 * (len(camera_order) - 1)
    water_z_idx = n_tilt_params + n_extrinsic_params
    lower = lower.copy()
    upper = upper.copy()
    lower[water_z_idx] = PINNED_WATER_Z - PIN_HALF_WIDTH
    upper[water_z_idx] = PINNED_WATER_Z + PIN_HALF_WIDTH
    return lower, upper


records = []
label = "n1.0_normalfixed_FALSE_water_z_PINNED_1.031_BOTH_PASSES (D-02: pinned + normal-free)"
print(f"\n=== {label} ===", flush=True)
diag3 = SolverDiagnostics()
diag_int = SolverDiagnostics()
timings, discard = {}, {}
t0 = time.time()
rec = {
    "label": label,
    "n_water": 1.0,
    "normal_fixed": False,
    "water_z_pinned": PINNED_WATER_Z,
}
try:
    # Both call sites import build_bounds independently (interface_estimation.py:277,
    # the first stage-3 pass, AND refinement.py:184, the second/intrinsic pass). Patching
    # only the first left water_z unpinned through the second pass (measured: it drifted
    # from 1.031 to 0.0424) -- both must be patched for the pin to hold end to end.
    ie_mod.build_bounds = _pinned_build_bounds
    ref_mod.build_bounds = _pinned_build_bounds
    scenario = create_scenario("realistic", seed=SEED)
    result, _det = calibrate_synthetic(
        scenario,
        n_water=1.0,
        refine_intrinsics=True,
        seed=SEED,
        diagnostics_out={
            "stage3_interface_optimization": diag3,
            "stage3_intrinsic_pass": diag_int,
        },
        timings_out=timings,
        discard_stats_out=discard,
        normal_fixed=False,
    )
    water_z_estimated = float(next(iter(result.cameras.values())).water_z)
    rec.update(
        elapsed_s=round(time.time() - t0, 1),
        degenerate_observations_at_solution=discard.get(
            "degenerate_observations_at_solution"
        ),
        discard_stats=dict(discard),
        optimality_interface=getattr(diag3, "optimality", None),
        optimality_intrinsic=getattr(diag_int, "optimality", None),
        cost_interface=getattr(diag3, "cost", None),
        cost_intrinsic=getattr(diag_int, "cost", None),
        status_interface=getattr(diag3, "status", None),
        status_intrinsic=getattr(diag_int, "status", None),
        water_z_estimated=water_z_estimated,
        water_z_error_from_gt_mm=round((water_z_estimated - PINNED_WATER_Z) * 1000, 6),
        bound_hit=bool(
            abs(water_z_estimated - (PINNED_WATER_Z - PIN_HALF_WIDTH)) < 1e-9
            or abs(water_z_estimated - (PINNED_WATER_Z + PIN_HALF_WIDTH)) < 1e-9
        ),
        timings=dict(timings),
        ok=True,
    )
except Exception as exc:  # probe must report, not die silently
    rec.update(
        ok=False,
        error=f"{type(exc).__name__}: {exc}",
        traceback=traceback.format_exc(),
        elapsed_s=round(time.time() - t0, 1),
    )
finally:
    ie_mod.build_bounds = _real_build_bounds
    ref_mod.build_bounds = _real_build_bounds

print(json.dumps(rec, indent=2, default=str), flush=True)
records.append(rec)
OUT.write_text(json.dumps(records, indent=2, default=str))

print("\n=== PROBE COMPLETE ===", flush=True)
