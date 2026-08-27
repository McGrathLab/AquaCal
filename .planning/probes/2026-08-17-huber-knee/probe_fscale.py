"""Does re-tuning the baseline's Huber knee change E1's accuracy?

Motivation (Finding 6, `2026-08-17-optimality-decomposition/FINDINGS.md`)
------------------------------------------------------------------------
E1 optimizes both arms under `f_scale = 1.0`. Measured at the solution:

    | solve                       | median |r| | past knee |
    | refractive,     interface   | 0.3357     |  4.5%     |
    | refractive,     intrinsic   | 0.3351     |  4.5%     |
    | non-refractive, interface   | 0.9444     | 47.7%     |
    | non-refractive, intrinsic   | 0.6174     | 29.4%     |

So the knee suits the refractive arm and not the baseline: a third to a half of
the baseline's residuals sit past it, in the linear regime where they are
down-weighted. The baseline is therefore optimized under a loss tuned to the
*other* arm's residual scale.

Finding 6 proposed the symmetric rule `f_scale = 3 x median|r|`, which
reproduces the status quo for the refractive arm almost exactly
(3 x 0.3357 = 1.007 vs the current 1.0) while moving the baseline to ~2.8 /
~1.9. That is the defensible form of the test: it changes nothing about the
method and only re-tunes the baseline.

**This is an open question, not a settled one.** Finding 4 settled *convergence*
(warm restarts recover no cost) under the current `f_scale`; it predicts nothing
about a different one. Direction of risk: a knee set too tight for the baseline
down-weights 29-48% of its residuals, so the current setting, if it biases
anything, *flatters* E1's refractive-to-non-refractive ratio.

Method
------
`scipy.optimize.least_squares` is monkeypatched in the two library modules that
import it, and the `f_scale` kwarg is overridden on the two non-refractive calls
only. The refractive arm is left untouched at 1.0 rather than set to its own
1.007, so it reproduces the control bit-for-bit and serves as the in-run check
that the patch hit only the arm it was meant to.

Comparison metric is **accuracy, not cost**. Changing `f_scale` changes the
objective, so costs are not comparable across runs -- the whole point of
Finding 6's protocol.

Control and treatment both run at the CURRENT sha. `verify_23_optblocks/` is at
`a7f0f25`, before Phase 24 touched `_optim_common.py`, so it cannot serve as the
control (see `.planning/knowledge-base.md` -- hold the library fixed when
testing a change).

Self-checks, all of which must pass before any number is believed
-----------------------------------------------------------------
1. Exactly 4 solver calls are seen. Anything else -> INDETERMINATE, no verdict.
   (The warm-restart probe reported a reassuring conclusion off zero completed
   restarts. Not again.)
2. Every call's incoming `f_scale` is 1.0, so the override is a real change.
3. In the treatment run, calls 1-2 (refractive) reproduce the control's costs
   exactly. If they do not, the call-ordering assumption is wrong and the
   attribution is meaningless.

Usage
-----
    python -u probe_fscale.py control
    python -u probe_fscale.py treatment
    python -u probe_fscale.py compare
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

# Finding 6's measured medians at the f_scale = 1.0 solution, times three.
# One pass, not a fixed point: re-solving moves the median slightly, so the new
# medians are recorded below and the distance from self-consistency is reported
# rather than iterated away. A shape check does not need the fixed point.
F_SCALE_INTERFACE = 3 * 0.9444  # 2.8332
F_SCALE_INTRINSIC = 3 * 0.6174  # 1.8522

#: Calls 1-2 are the refractive arm, 3-4 the non-refractive arm. Established by
#: `2026-08-17-optimality-decomposition/probe_optimality_blocks.py`, and
#: re-verified here by self-check 3 rather than assumed.
OVERRIDES = {3: F_SCALE_INTERFACE, 4: F_SCALE_INTRINSIC}

CALLS: list[dict] = []


def run_e1(mode: str) -> int:
    """Run E1 once, optionally overriding the baseline arm's f_scale."""
    from aquacal.calibration import interface_estimation, refinement

    real_ls = interface_estimation.least_squares
    counter = {"n": 0}
    treat = mode == "treatment"

    def patched(*args, **kwargs):
        counter["n"] += 1
        n = counter["n"]
        incoming = kwargs.get("f_scale")
        applied = incoming
        if treat and n in OVERRIDES:
            applied = OVERRIDES[n]
            kwargs["f_scale"] = applied
            print(f"  [call {n}] f_scale {incoming} -> {applied}", flush=True)
        else:
            print(f"  [call {n}] f_scale {incoming} (unchanged)", flush=True)

        result = real_ls(*args, **kwargs)

        resid = np.asarray(result.fun, dtype=float)
        abs_r = np.abs(resid)
        CALLS.append(
            {
                "call": n,
                "f_scale_incoming": incoming,
                "f_scale_applied": applied,
                "cost": float(result.cost),
                "optimality": float(result.optimality),
                "status": int(result.status),
                "nfev": int(result.nfev),
                "n_params": int(np.asarray(result.x).size),
                "n_residuals": int(resid.size),
                "median_abs_r": float(np.median(abs_r)),
                "p90_abs_r": float(np.percentile(abs_r, 90)),
                # Self-consistency of the symmetric rule at the NEW solution.
                "implied_f_scale": float(3 * np.median(abs_r)),
            }
        )
        return result

    interface_estimation.least_squares = patched
    refinement.least_squares = patched

    from experiments import e1_refractive_comparison as e1

    out_dir = PROBE_DIR / f"e1_{mode}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Running E1 [{mode}] -> {out_dir}", flush=True)
    rc = e1.main(["--out", str(out_dir)])
    print(f"\nE1 [{mode}] exited {rc}; saw {len(CALLS)} solver calls", flush=True)

    (PROBE_DIR / f"calls_{mode}.json").write_text(
        json.dumps({"mode": mode, "calls": CALLS}, indent=2), encoding="utf-8"
    )
    return rc


def compare() -> int:
    """Compare accuracy between the two runs. Refuses to conclude on bad input."""
    import pandas as pd

    problems: list[str] = []
    calls = {}
    for mode in ("control", "treatment"):
        p = PROBE_DIR / f"calls_{mode}.json"
        if not p.exists():
            problems.append(f"missing {p.name} -- run `{mode}` first")
            continue
        calls[mode] = json.loads(p.read_text(encoding="utf-8"))["calls"]

    if problems:
        print("INDETERMINATE:\n  " + "\n  ".join(problems))
        return 1

    # Self-check 1: exactly four calls each.
    for mode, cl in calls.items():
        if len(cl) != 4:
            problems.append(f"{mode}: expected 4 solver calls, saw {len(cl)}")

    # Self-check 2: the override was a real change.
    for c in calls["treatment"]:
        if c["call"] in OVERRIDES:
            if c["f_scale_incoming"] != 1.0:
                problems.append(
                    f"treatment call {c['call']}: incoming f_scale "
                    f"{c['f_scale_incoming']}, expected 1.0"
                )
            if c["f_scale_applied"] == c["f_scale_incoming"]:
                problems.append(f"treatment call {c['call']}: override did not apply")

    # Self-check 3: the untouched refractive arm reproduces the control.
    if not problems:
        for n in (1, 2):
            a = next(c for c in calls["control"] if c["call"] == n)["cost"]
            b = next(c for c in calls["treatment"] if c["call"] == n)["cost"]
            if a != b:
                rel = abs(a - b) / max(abs(a), 1e-30)
                problems.append(
                    f"call {n} (refractive, untouched) moved: {a!r} -> {b!r} "
                    f"(rel {rel:.3e}) -- call-ordering assumption is wrong"
                )

    if problems:
        print("INDETERMINATE -- self-checks failed, no verdict:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("Self-checks passed (4 calls, override applied, refractive arm identical).\n")

    for mode in ("control", "treatment"):
        print(f"--- {mode} solver calls")
        for c in calls[mode]:
            print(
                f"  call {c['call']}: f_scale={c['f_scale_applied']:.4f} "
                f"cost={c['cost']:.6f} median|r|={c['median_abs_r']:.4f} "
                f"implied_f_scale={c['implied_f_scale']:.4f} "
                f"nfev={c['nfev']} status={c['status']}"
            )
        print()

    rows = []
    for depth_metric, fname, cols in (
        (
            "exp3",
            "exp3_xy_vs_z_anisotropy.csv",
            ["xy_rmse_mm", "z_rmse_mm", "anisotropy_ratio"],
        ),
        ("exp2", "exp2_depth_generalization.csv", ["signed_mean_mm", "rmse_mm"]),
    ):
        dfs = {}
        for mode in ("control", "treatment"):
            f = PROBE_DIR / f"e1_{mode}" / fname
            if not f.exists():
                print(f"INDETERMINATE: missing {f}")
                return 1
            dfs[mode] = pd.read_csv(f)
        merged = dfs["control"].merge(
            dfs["treatment"], on=["test_depth_m", "model"], suffixes=("_ctl", "_trt")
        )
        for _, r in merged.iterrows():
            for col in cols:
                rows.append(
                    {
                        "source": depth_metric,
                        "depth_m": r["test_depth_m"],
                        "model": r["model"],
                        "metric": col,
                        "control": r[f"{col}_ctl"],
                        "treatment": r[f"{col}_trt"],
                    }
                )

    df = pd.DataFrame(rows)
    df["abs_delta"] = df["treatment"] - df["control"]
    df["rel_delta"] = df["abs_delta"] / df["control"].abs().replace(0, np.nan)
    df.to_csv(PROBE_DIR / "fscale_accuracy_comparison.csv", index=False)

    print("=== Non-refractive (baseline) arm -- the arm that was re-tuned")
    nr = df[df["model"] == "non_refractive"]
    for metric in nr["metric"].unique():
        sub = nr[nr["metric"] == metric]
        print(
            f"  {metric:18s} max|rel change| = {sub['rel_delta'].abs().max():8.4%}   "
            f"mean = {sub['rel_delta'].mean():+8.4%}"
        )

    print("\n=== Refractive arm -- untouched, must be identical")
    rf = df[df["model"] == "refractive"]
    print(f"  max|abs change| across all metrics = {rf['abs_delta'].abs().max():.3e}")

    # The headline: does the ratio move?
    print("\n=== E1's z_rmse ratio (non_refractive / refractive), by depth")
    z = df[(df["metric"] == "z_rmse_mm")]
    for depth in sorted(z["depth_m"].unique()):
        d = z[z["depth_m"] == depth]
        nrr = d[d["model"] == "non_refractive"].iloc[0]
        rfr = d[d["model"] == "refractive"].iloc[0]
        r_ctl = nrr["control"] / rfr["control"]
        r_trt = nrr["treatment"] / rfr["treatment"]
        print(
            f"  depth {depth:>4} m: control {r_ctl:8.2f}x  ->  "
            f"treatment {r_trt:8.2f}x   ({(r_trt / r_ctl - 1):+.2%})"
        )

    print(f"\nWrote {PROBE_DIR / 'fscale_accuracy_comparison.csv'}")
    return 0


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode in ("control", "treatment"):
        return run_e1(mode)
    if mode == "compare":
        return compare()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
