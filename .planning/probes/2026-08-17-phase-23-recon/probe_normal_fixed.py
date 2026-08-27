"""SCRATCH PROBE — does FIX-02 (normal_fixed=False) interact with E1's non-refractive arm?

Mirrors e1_refractive_comparison._run_one_model exactly, adding normal_fixed as a knob.
Writes ONLY to the scratchpad. Touches no tracked file.

Baseline to beat (committed, MANUSCRIPT-FINDINGS):
  n=1.0, normal_fixed=True  -> degenerate 14,949 ; optimality ~9e+02
"""

import json
import sys
import time
import traceback
from pathlib import Path

from aquacal.calibration._observability import SolverDiagnostics
from aquacal.datasets import calibrate_synthetic, create_scenario

OUT = Path(sys.argv[1])
SEED = 42

ARMS = [
    ("n1.0_normalfixed_TRUE  (committed baseline)", 1.0, True),
    ("n1.0_normalfixed_FALSE (FIX-02 alone)", 1.0, False),
    ("n1.333_normalfixed_FALSE (refractive control)", 1.333, False),
]

records = []
for label, n_water, normal_fixed in ARMS:
    print(f"\n=== {label} ===", flush=True)
    diag3 = SolverDiagnostics()
    diag_int = SolverDiagnostics()
    timings, discard = {}, {}
    t0 = time.time()
    rec = {"label": label, "n_water": n_water, "normal_fixed": normal_fixed}
    try:
        scenario = create_scenario("realistic", seed=SEED)
        result, _det = calibrate_synthetic(
            scenario,
            n_water=n_water,
            refine_intrinsics=True,
            seed=SEED,
            diagnostics_out={
                "stage3_interface_optimization": diag3,
                "stage3_intrinsic_pass": diag_int,
            },
            timings_out=timings,
            discard_stats_out=discard,
            normal_fixed=normal_fixed,
        )
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
            water_z_estimated=float(next(iter(result.cameras.values())).water_z),
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
    print(json.dumps(rec, indent=2, default=str), flush=True)
    records.append(rec)
    OUT.write_text(json.dumps(records, indent=2, default=str))

print("\n=== PROBE COMPLETE ===", flush=True)
OUT.write_text(json.dumps(records, indent=2, default=str))
