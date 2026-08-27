"""Decompose each stage-3 solver call's first-order optimality by parameter block.

Motivation (DEGEN-05, opened 2026-08-17)
----------------------------------------
Phase 23's verification run left E1's non-refractive arm reporting
``optimality_intrinsic`` = 92.78 while the refractive arm reports 0.0247 on the
same scenario and seed -- a ~2000x gap. The phase documents attribute the rise
to pinning ``water_z`` against a ~2e-12-wide box. That explanation accounts for
at most the 49.65 (unpinned) -> 92.78 (pinned) step; it cannot explain the
baseline, because the unpinned arm has no pin at all and still reads 49.65.

This probe answers the question the aggregate number cannot: *where does the
residual live?* A KKT residual concentrated in a pinned or bounded slot is
benign. One spread across extrinsics and board poses means the arm terminates
non-stationary -- which would make E1's error larger than the true optimum and
therefore *inflate* the refractive-to-non-refractive ratio.

Method
------
``scipy.optimize.least_squares`` is monkeypatched in the two library modules
that import it. Each call's ``OptimizeResult`` carries ``grad`` (J^T f),
``active_mask``, and ``optimality``. For the ``trf`` method (selected whenever
bounds are finite, which is always here) scipy reports

    optimality = ||g * v||_inf

where ``v`` is the Coleman-Li scaling vector. We reimplement ``v`` and assert
our reconstruction reproduces scipy's reported ``optimality`` before trusting
any decomposition -- if the reconstruction disagrees, the block attribution is
meaningless and the probe says so rather than reporting numbers.

Note the direction the CL scaling actually pushes: for a parameter sitting on a
bound, ``v`` is its distance to that bound, so ``v -> 0`` and the parameter's
contribution *vanishes*. This predicts the pinned ``water_z`` contributes ~0 to
``optimality``, which is the opposite of the documented explanation. That
prediction is exactly what this probe tests.

Block layout is derived from the bounds vector rather than assumed, using the
structure ``build_bounds`` creates:
  - tilt (2 params, only when normal_fixed=False): bounds [-0.2, 0.2]
  - extrinsics: 6*(n_cams-1), unbounded
  - water_z: finite bounds, the first finite-bounded run after the tilt block
  - board poses: 6*n_frames, unbounded
  - intrinsics (only when refine_intrinsics=True): trailing finite-bounded block

Usage
-----
    python -u .planning/probes/2026-08-17-optimality-decomposition/probe_optimality_blocks.py

Writes ``optimality_blocks.json`` beside this file. E1's own artifacts go to a
git-ignored directory and are not the output of interest here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

PROBE_DIR = Path(__file__).resolve().parent
OUT_JSON = PROBE_DIR / "optimality_blocks.json"
E1_OUT_DIR = REPO_ROOT / "experiments" / "verify_23_optblocks"

CAPTURES: list[dict] = []


def cl_scaling_vector(x, g, lb, ub):
    """Reimplementation of scipy.optimize._lsq.common.CL_scaling_vector.

    For each coordinate, ``v`` is the distance to the bound the negative
    gradient points toward, or 1 where that bound is infinite.
    """
    v = np.ones_like(x)
    mask = (g < 0) & np.isfinite(ub)
    v[mask] = ub[mask] - x[mask]
    mask = (g > 0) & np.isfinite(lb)
    v[mask] = x[mask] - lb[mask]
    return v


def derive_blocks(lb, ub, n_params):
    """Derive the semantic parameter blocks from the bounds vector."""
    n_tilt = 2 if (np.isfinite(lb[0]) and np.isclose(lb[0], -0.2)) else 0

    # water_z is the first finite-lower-bound index at or after the tilt block.
    water_z_idx = None
    for i in range(n_tilt, n_params):
        if np.isfinite(lb[i]):
            water_z_idx = i
            break
    if water_z_idx is None:
        raise RuntimeError("could not locate water_z slot: no finite lower bound found")

    # Contiguous run of finite bounds starting at water_z_idx (1 when shared).
    n_wz = 0
    while water_z_idx + n_wz < n_params and np.isfinite(lb[water_z_idx + n_wz]):
        n_wz += 1

    # Trailing finite-bounded block is intrinsics (4 per camera), if present.
    n_intr = 0
    j = n_params - 1
    while j >= 0 and np.isfinite(lb[j]):
        n_intr += 1
        j -= 1
    if n_intr == n_wz and water_z_idx + n_wz == n_params:
        n_intr = 0  # the trailing run *is* the water_z run

    n_cams = (water_z_idx - n_tilt) // 6 + 1
    pose_start = water_z_idx + n_wz
    pose_end = n_params - n_intr
    n_frames = (pose_end - pose_start) // 6

    blocks = {}
    if n_tilt:
        blocks["tilt"] = (0, n_tilt)
    blocks["extrinsics"] = (n_tilt, water_z_idx)
    blocks["water_z"] = (water_z_idx, water_z_idx + n_wz)
    blocks["board_poses"] = (pose_start, pose_end)
    if n_intr:
        blocks["intrinsics"] = (pose_end, n_params)

    return blocks, {
        "n_cams_derived": int(n_cams),
        "n_frames_derived": int(n_frames),
        "n_tilt": int(n_tilt),
        "n_water_z": int(n_wz),
        "n_intrinsics": int(n_intr),
    }


def capture(result, bounds, label):
    """Decompose one least_squares result, validating against scipy's number."""
    x = np.asarray(result.x, dtype=float)
    g = np.asarray(result.grad, dtype=float)
    lb, ub = (np.asarray(b, dtype=float) for b in bounds)
    lb = np.broadcast_to(lb, x.shape).copy()
    ub = np.broadcast_to(ub, x.shape).copy()

    v = cl_scaling_vector(x, g, lb, ub)
    scaled = np.abs(g * v)
    reconstructed = float(scaled.max())
    reported = float(result.optimality)

    # The decomposition is only meaningful if we reproduce scipy's own number.
    denom = max(abs(reported), 1e-30)
    rel_err = abs(reconstructed - reported) / denom
    trustworthy = bool(rel_err < 1e-6)

    blocks, layout = derive_blocks(lb, ub, x.size)

    per_block = {}
    for name, (start, stop) in blocks.items():
        seg = scaled[start:stop]
        if seg.size == 0:
            continue
        local_arg = int(np.argmax(seg))
        per_block[name] = {
            "n_params": int(stop - start),
            "max_abs_scaled_grad": float(seg.max()),
            "share_of_reported_optimality": float(seg.max() / denom),
            "argmax_global_index": int(start + local_arg),
            "max_abs_raw_grad": float(np.abs(g[start:stop]).max()),
            "n_at_bound": int(np.count_nonzero(result.active_mask[start:stop])),
            "min_bound_gap": (
                float(np.min(ub[start:stop] - lb[start:stop]))
                if np.all(np.isfinite(ub[start:stop] - lb[start:stop]))
                else None
            ),
        }

    dominant = max(per_block.items(), key=lambda kv: kv[1]["max_abs_scaled_grad"])[0]

    rec = {
        "label": label,
        "n_params": int(x.size),
        "reported_optimality": reported,
        "reconstructed_optimality": reconstructed,
        "reconstruction_relative_error": float(rel_err),
        "decomposition_trustworthy": trustworthy,
        "dominant_block": dominant,
        "status": int(result.status),
        "cost": float(result.cost),
        "n_at_bound_total": int(np.count_nonzero(result.active_mask)),
        "layout": layout,
        "blocks": per_block,
    }
    CAPTURES.append(rec)

    print(f"\n--- capture {len(CAPTURES)}: {label} ---", flush=True)
    print(f"  n_params={x.size}  cost={result.cost:.6f}  status={result.status}")
    print(
        f"  optimality reported={reported:.6g}  reconstructed={reconstructed:.6g}  "
        f"rel_err={rel_err:.2e}  trustworthy={trustworthy}"
    )
    print(f"  dominant block: {dominant}")
    for name, d in per_block.items():
        print(
            f"    {name:<12} n={d['n_params']:<4} "
            f"max|g*v|={d['max_abs_scaled_grad']:.6g} "
            f"({100 * d['share_of_reported_optimality']:.2f}% of reported)  "
            f"max|g|={d['max_abs_raw_grad']:.6g}  at_bound={d['n_at_bound']}"
        )


def main() -> int:
    from aquacal.calibration import interface_estimation, refinement

    real_ls = interface_estimation.least_squares
    counter = {"n": 0}

    def patched(*args, **kwargs):
        result = real_ls(*args, **kwargs)
        counter["n"] += 1
        bounds = kwargs.get("bounds")
        if bounds is None and len(args) > 2:
            bounds = args[2]
        try:
            if bounds is not None:
                capture(result, bounds, f"call_{counter['n']}")
            else:
                print(f"  (call {counter['n']}: no bounds kwarg; skipped)", flush=True)
        except Exception as exc:  # never let the probe break the run
            print(f"  !! capture failed on call {counter['n']}: {exc}", flush=True)
        return result

    interface_estimation.least_squares = patched
    refinement.least_squares = patched

    from experiments import e1_refractive_comparison as e1

    E1_OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Running E1 with instrumented least_squares -> {E1_OUT_DIR}", flush=True)
    rc = e1.main(["--out", str(E1_OUT_DIR)])
    print(f"\nE1 exited {rc}; captured {len(CAPTURES)} solver calls", flush=True)

    OUT_JSON.write_text(json.dumps({"captures": CAPTURES}, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
