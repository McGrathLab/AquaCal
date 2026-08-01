"""Discriminator for plan 28's hard stop.

The E6 re-run moved 63 of 308 cells (worst rel 6.1e-5). Two candidate causes:
  (a) plan 27's diagnostics_out/discard_stats_out sinks are not inert, or
  (b) E6 is simply not bit-reproducible run-to-run.

This runs the SAME configuration TWICE on IDENTICAL code. If the two runs differ,
(b) is proven and plan 27 is exonerated -- no code change can explain a difference
between two runs of the same code.

Writes only to temp dirs; never touches experiments/results/.
"""

import tempfile
from pathlib import Path

import experiments.e6_generalization_sweep as m

CONFIGS_TO_PROBE = ["scale_half_scale", "index_1.36"]

for key in CONFIGS_TO_PROBE:
    cfg = next(c for c in m.build_axis_configurations() if c["config_key"] == key)
    print(f"\n=== {key} (n_frames={m.BASELINE_N_FRAMES}, seed=42) ===", flush=True)
    vals = []
    for i in (1, 2):
        with tempfile.TemporaryDirectory() as td:
            rec = m.run_configuration(
                cfg, 42, m.BASELINE_N_FRAMES, Path(td), force=True
            )
            met = rec.get("metrics") or {}
            rms = met.get("reprojection_rms_px")
            focal = met.get("focal_error_pct_mean")
            vals.append((rms, focal))
            print(f"  run {i}: rms={rms!r}  focal_err_pct={focal!r}", flush=True)

    (r1, f1), (r2, f2) = vals
    print(f"  rms identical  : {r1 == r2}", flush=True)
    print(f"  focal identical: {f1 == f2}", flush=True)
    if r1 != r2:
        print(
            f"  rms delta={r2 - r1:+.6e} rel={abs(r2 - r1) / abs(r1):.3e}", flush=True
        )
    if f1 is not None and f2 is not None and f1 != f2:
        print(
            f"  focal delta={f2 - f1:+.6e} rel={abs(f2 - f1) / abs(f1):.3e}", flush=True
        )

print("\n=== PROBE COMPLETE ===", flush=True)
