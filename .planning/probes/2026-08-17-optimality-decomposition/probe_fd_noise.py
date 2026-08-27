"""FD-noise discriminator: is the reported `optimality` measuring conditioning, or Jacobian error?

Question
--------
`optimality` is unstable at a fixed solution (92.78 -> 27.58 -> 2.16 while cost
moves 1.8e-9). Two candidates:

  1. extreme gradient sensitivity in a narrow, high-curvature valley
  2. finite-difference Jacobian noise dominating a near-zero true gradient

The gradient is ``J^T f`` with ``J`` built by finite differences. Near a minimum
the true gradient is ~0, so FD error -- which scales with residual magnitude --
can dominate what gets reported. If so, `optimality` in **every** benchmark
record this library writes is partly measuring Jacobian noise, not conditioning.

Method
------
At each solver call's own solution, recompute the gradient with the identical
downstream formula but different Jacobians:

  - ``production``  -- the library's own FD Jacobian callable (what the solver used)
  - ``3-point``     -- central differences, materially more accurate than 2-point
  - ``2-point`` at several ``rel_step`` values -- a step-size sensitivity sweep

Everything downstream is held fixed: the same robust-loss scaling scipy applies
internally, then the same Coleman-Li scaled infinity norm. So any difference in
the resulting optimality is attributable to ``J`` alone.

**Self-validation gate.** The probe first reproduces scipy's *reported*
optimality using the production Jacobian. If that reconstruction disagrees, the
loss/scaling pipeline is wrong and every downstream comparison is meaningless --
the probe reports ``pipeline_validated: false`` and draws no conclusion. This is
deliberate: the previous probe in this directory defaulted to a reassuring
verdict having measured nothing.

Reading the result
------------------
  - high-accuracy Jacobians give a MUCH smaller optimality  -> FD noise dominates,
    hypothesis 2 confirmed, and the reported number is not a conditioning measure
  - all Jacobians agree                                     -> the gradient is real,
    hypothesis 1, and the instability is genuine curvature sensitivity

Usage
-----
    python -u .planning/probes/2026-08-17-optimality-decomposition/probe_fd_noise.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

PROBE_DIR = Path(__file__).resolve().parent
OUT_JSON = PROBE_DIR / "fd_noise.json"
E1_OUT_DIR = REPO_ROOT / "experiments" / "verify_23_fdnoise"

RECORDS: list[dict] = []
EPS = np.finfo(float).eps


def huber_rho(f, f_scale):
    """Reproduce scipy's huber loss triple (rho, rho', rho'') for residuals f."""
    z = (f / f_scale) ** 2
    rho = np.empty((3, f.size))
    mask = z <= 1
    rho[0, mask] = z[mask]
    rho[0, ~mask] = 2 * z[~mask] ** 0.5 - 1
    rho[1, mask] = 1
    rho[1, ~mask] = z[~mask] ** -0.5
    rho[2, mask] = 0
    rho[2, ~mask] = -0.5 * z[~mask] ** -1.5
    rho[0] *= f_scale**2
    rho[2] /= f_scale**2
    return rho


def scaled_gradient(J, f, loss, f_scale):
    """Apply scipy's robust-loss scaling, then return g = J^T f."""
    if loss in (None, "linear"):
        return J.T.dot(f)
    rho = huber_rho(f, f_scale)
    J_scale = rho[1] + 2 * rho[2] * f**2
    J_scale[J_scale < EPS] = EPS
    J_scale **= 0.5
    f_mod = f * rho[1] / J_scale
    return (J * J_scale[:, np.newaxis]).T.dot(f_mod)


def cl_scaled_inf_norm(g, x, lb, ub):
    """scipy's trf optimality: ||g * v||_inf with v the Coleman-Li scaling."""
    v = np.ones_like(x)
    mask = (g < 0) & np.isfinite(ub)
    v[mask] = ub[mask] - x[mask]
    mask = (g > 0) & np.isfinite(lb)
    v[mask] = x[mask] - lb[mask]
    return float(np.max(np.abs(g * v)))


def main() -> int:
    from scipy.optimize._numdiff import approx_derivative, group_columns

    from aquacal.calibration import interface_estimation, refinement

    real_ls = interface_estimation.least_squares
    state = {"n": 0}

    def patched(*args, **kwargs):
        result = real_ls(*args, **kwargs)
        state["n"] += 1
        label = f"call_{state['n']}"

        fun = args[0]
        jac = kwargs.get("jac")
        fargs = kwargs.get("args", ())
        loss = kwargs.get("loss", "linear")
        f_scale = kwargs.get("f_scale", 1.0)
        bounds = kwargs.get("bounds")
        if bounds is None and len(args) > 2:
            bounds = args[2]

        print(f"\n--- {label} ---", flush=True)
        print(
            f"  reported optimality={result.optimality:.6g}  cost={result.cost:.10g} "
            f"loss={loss} f_scale={f_scale}",
            flush=True,
        )

        rec = {
            "label": label,
            "reported_optimality": float(result.optimality),
            "cost": float(result.cost),
            "loss": str(loss),
            "f_scale": float(f_scale),
            "variants": {},
        }

        try:
            if jac is None or bounds is None:
                raise RuntimeError("jac or bounds not passed as keywords")

            x = np.asarray(result.x, dtype=float)
            lb, ub = (
                np.broadcast_to(np.asarray(b, float), x.shape).copy() for b in bounds
            )
            f0 = np.asarray(result.fun, dtype=float)

            # --- production Jacobian: the one the solver actually used ---
            t0 = time.time()
            J_prod = np.asarray(jac(x, *fargs), dtype=float)
            t_prod = time.time() - t0

            g_prod = scaled_gradient(J_prod, f0.copy(), loss, f_scale)
            opt_prod = cl_scaled_inf_norm(g_prod, x, lb, ub)

            # --- SELF-VALIDATION: must reproduce scipy's reported number ---
            rel_err = abs(opt_prod - result.optimality) / max(
                abs(result.optimality), 1e-30
            )
            validated = bool(rel_err < 1e-4)
            rec["pipeline_validated"] = validated
            rec["reconstruction_relative_error"] = float(rel_err)
            print(
                f"  production J: optimality={opt_prod:.6g} "
                f"(rel_err vs reported {rel_err:.2e}) validated={validated} "
                f"[{t_prod:.1f}s]",
                flush=True,
            )
            rec["variants"]["production"] = {
                "optimality": opt_prod,
                "max_abs_grad": float(np.abs(g_prod).max()),
                "seconds": t_prod,
            }

            if not validated:
                print(
                    "  !! reconstruction disagrees with scipy -- refusing to compare "
                    "Jacobians; no conclusion drawn",
                    flush=True,
                )
                RECORDS.append(rec)
                return result

            # Reuse the production Jacobian's own sparsity so the high-accuracy
            # variants cost ~2 evals per column group instead of 2*n_params.
            structure = (J_prod != 0).astype(np.int8)
            groups = group_columns(structure)
            sparsity = (structure, groups)
            rec["n_column_groups"] = int(groups.max() + 1)

            def wrapped(p):
                return np.asarray(fun(p, *fargs), dtype=float)

            variants = [
                ("3-point", {"method": "3-point"}),
                ("2-point_rel_1e-6", {"method": "2-point", "rel_step": 1e-6}),
                ("2-point_rel_1e-8", {"method": "2-point", "rel_step": 1e-8}),
                ("2-point_rel_1e-10", {"method": "2-point", "rel_step": 1e-10}),
            ]
            for name, opts in variants:
                t1 = time.time()
                J_v = approx_derivative(
                    wrapped, x, f0=f0, bounds=(lb, ub), sparsity=sparsity, **opts
                )
                J_v = np.asarray(
                    J_v.todense() if hasattr(J_v, "todense") else J_v, float
                )
                secs = time.time() - t1
                g_v = scaled_gradient(J_v, f0.copy(), loss, f_scale)
                opt_v = cl_scaled_inf_norm(g_v, x, lb, ub)
                ratio = opt_prod / max(opt_v, 1e-30)
                rec["variants"][name] = {
                    "optimality": opt_v,
                    "max_abs_grad": float(np.abs(g_v).max()),
                    "ratio_production_over_this": float(ratio),
                    "max_abs_jacobian_diff_vs_production": float(
                        np.abs(J_v - J_prod).max()
                    ),
                    "seconds": secs,
                }
                print(
                    f"    {name:<18} optimality={opt_v:.6g}  "
                    f"production/this={ratio:.4g}  "
                    f"max|dJ|={np.abs(J_v - J_prod).max():.3g}  [{secs:.1f}s]",
                    flush=True,
                )

            best = rec["variants"].get("3-point", {}).get("optimality")
            if best is not None:
                rec["fd_noise_ratio"] = float(opt_prod / max(best, 1e-30))
                rec["verdict"] = (
                    "FD NOISE DOMINATES"
                    if rec["fd_noise_ratio"] > 10
                    else "gradient is real (FD not the driver)"
                )
                print(
                    f"  => {rec['verdict']} (ratio {rec['fd_noise_ratio']:.4g})",
                    flush=True,
                )
        except Exception as exc:
            rec["error"] = str(exc)
            rec["verdict"] = "INDETERMINATE -- probe error"
            print(f"  !! {exc}", flush=True)

        RECORDS.append(rec)
        return result

    interface_estimation.least_squares = patched
    refinement.least_squares = patched

    from experiments import e1_refractive_comparison as e1

    E1_OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Running E1 with FD-noise instrumentation -> {E1_OUT_DIR}", flush=True)
    rc = e1.main(["--out", str(E1_OUT_DIR)])
    print(f"\nE1 exited {rc}; instrumented {len(RECORDS)} solver calls", flush=True)

    OUT_JSON.write_text(json.dumps({"records": RECORDS}, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
