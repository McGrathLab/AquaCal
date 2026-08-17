"""Warm-restart test: is E1's non-refractive arm under-converged, or genuinely stalled?

Question
--------
Both E1 arms terminate on ``ftol`` with gradients far above ``gtol`` (non-refractive
92.78, refractive 0.0247, gtol 1e-8). That means "cost stopped moving", not
"gradient vanished". If the solver stalled prematurely, the *baseline* arm is
under-optimized -- which inflates E1's refractive-to-non-refractive ratio,
because the under-converged arm is the denominator.

Method
------
After each ``least_squares`` call returns, restart it from its own solution with
identical settings. A restart resets the trust-region radius, so:

  - cost drops materially  -> the first solve stalled early; the arm is
    UNDER-CONVERGED and the comparison is not currently fair.
  - cost does not move     -> the arm sits at a genuine (if ill-conditioned)
    minimum; the comparison stands as measured.

Two successive restarts are run, so a slow monotone crawl is distinguishable
from a single trust-region reset artifact.

Also recorded, nearly free: where each arm's residuals sit relative to the Huber
knee (``f_scale``). The hypothesis is that the non-refractive arm's residuals are
mostly *past* the knee, in the linear regime where curvature collapses and
``ftol`` trips early, while the refractive arm's sit inside it.

Usage
-----
    python -u .planning/probes/2026-08-17-optimality-decomposition/probe_warm_restart.py

Writes ``warm_restart.json`` beside this file. Runtime ~2x a normal E1 run
(each solve is executed three times), so roughly 20-25 minutes.
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
OUT_JSON = PROBE_DIR / "warm_restart.json"
E1_OUT_DIR = REPO_ROOT / "experiments" / "verify_23_optblocks"

RECORDS: list[dict] = []
N_RESTARTS = 2


def residual_stats(fun, f_scale):
    """Where do residuals sit relative to the Huber knee?"""
    r = np.abs(np.asarray(fun, dtype=float))
    if r.size == 0:
        return {}
    stats = {
        "n_residuals": int(r.size),
        "median_abs_residual": float(np.median(r)),
        "mean_abs_residual": float(r.mean()),
        "p90_abs_residual": float(np.percentile(r, 90)),
        "max_abs_residual": float(r.max()),
        "f_scale": None if f_scale is None else float(f_scale),
    }
    if f_scale is not None:
        stats["fraction_past_huber_knee"] = float(
            np.count_nonzero(r > f_scale) / r.size
        )
    return stats


def main() -> int:
    from aquacal.calibration import interface_estimation, refinement

    real_ls = interface_estimation.least_squares
    state = {"n": 0, "inner": False}

    def patched(*args, **kwargs):
        if state["inner"]:
            return real_ls(*args, **kwargs)

        t0 = time.time()
        result = real_ls(*args, **kwargs)
        base_seconds = time.time() - t0
        state["n"] += 1
        label = f"call_{state['n']}"

        rec = {
            "label": label,
            "base": {
                "cost": float(result.cost),
                "optimality": float(result.optimality),
                "status": int(result.status),
                "nfev": int(result.nfev),
                "seconds": base_seconds,
            },
            "restarts": [],
            "residuals": residual_stats(result.fun, kwargs.get("f_scale")),
        }

        print(f"\n--- {label} ---", flush=True)
        print(
            f"  base: cost={result.cost:.10g} optimality={result.optimality:.6g} "
            f"status={result.status} nfev={result.nfev} ({base_seconds:.1f}s)",
            flush=True,
        )
        if rec["residuals"].get("fraction_past_huber_knee") is not None:
            print(
                f"  residuals: median={rec['residuals']['median_abs_residual']:.4f} "
                f"p90={rec['residuals']['p90_abs_residual']:.4f} "
                f"f_scale={rec['residuals']['f_scale']} "
                f"past_knee={100 * rec['residuals']['fraction_past_huber_knee']:.1f}%",
                flush=True,
            )

        # Warm restarts from the solver's own solution.
        state["inner"] = True
        prev_cost = float(result.cost)
        current = result
        try:
            for k in range(N_RESTARTS):
                t1 = time.time()
                # x0 may arrive positionally (args[1]) or as a keyword. Rebuilding
                # it the wrong way raises "got multiple values for argument 'x0'",
                # which on the first run silently produced zero restarts.
                if len(args) >= 2:
                    restarted = real_ls(args[0], current.x, *args[2:], **kwargs)
                else:
                    restart_kwargs = dict(kwargs)
                    restart_kwargs["x0"] = current.x
                    restarted = real_ls(*args, **restart_kwargs)
                secs = time.time() - t1
                new_cost = float(restarted.cost)
                drop = prev_cost - new_cost
                rel_drop = drop / max(abs(prev_cost), 1e-30)
                rec["restarts"].append(
                    {
                        "index": k + 1,
                        "cost": new_cost,
                        "cost_drop": float(drop),
                        "relative_cost_drop": float(rel_drop),
                        "optimality": float(restarted.optimality),
                        "status": int(restarted.status),
                        "nfev": int(restarted.nfev),
                        "seconds": secs,
                    }
                )
                print(
                    f"  restart {k + 1}: cost={new_cost:.10g} "
                    f"drop={drop:.6g} ({100 * rel_drop:.4f}%) "
                    f"optimality={restarted.optimality:.6g} "
                    f"nfev={restarted.nfev} ({secs:.1f}s)",
                    flush=True,
                )
                prev_cost = new_cost
                current = restarted
        except Exception as exc:
            print(f"  !! restart failed: {exc}", flush=True)
        finally:
            state["inner"] = False

        # Never default to a conclusion. If no restart actually ran, the probe
        # measured nothing and must say so rather than reporting "stalled",
        # which is what the 2026-08-17 first run wrongly did.
        if not rec["restarts"]:
            rec["total_relative_cost_drop"] = None
            rec["verdict"] = "INDETERMINATE -- no restart completed"
            print(f"  => {rec['verdict']}", flush=True)
        else:
            total_rel = (float(result.cost) - prev_cost) / max(
                abs(float(result.cost)), 1e-30
            )
            rec["total_relative_cost_drop"] = float(total_rel)
            rec["verdict"] = (
                "UNDER-CONVERGED" if total_rel > 1e-6 else "stalled at/near a minimum"
            )
            print(
                f"  => total relative cost drop {100 * total_rel:.6f}%  "
                f"[{rec['verdict']}]",
                flush=True,
            )

        RECORDS.append(rec)
        return result

    interface_estimation.least_squares = patched
    refinement.least_squares = patched

    from experiments import e1_refractive_comparison as e1

    E1_OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Running E1 with warm-restart instrumentation -> {E1_OUT_DIR}", flush=True)
    rc = e1.main(["--out", str(E1_OUT_DIR)])
    print(f"\nE1 exited {rc}; instrumented {len(RECORDS)} solver calls", flush=True)

    OUT_JSON.write_text(
        json.dumps({"n_restarts": N_RESTARTS, "records": RECORDS}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_JSON}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
