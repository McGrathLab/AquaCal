"""
End-to-end confirmation: re-run E1's BOTH arms with water_z PINNED at ground
truth, and compare every published quantity against tonight's free-water_z run.

Pinning is done by monkeypatching build_bounds to a +/-1e-9 interval around
ground truth (scipy requires lb < ub strictly). No repo file is modified.

The forward-model probe already proved water_z is an exact null direction at
n_water = 1.0. This closes the loop through triangulation and the depth sweep,
which are separate code paths from compute_residuals.

Writes nothing under experiments/.
"""

import numpy as np

import aquacal.calibration.interface_estimation as ie
import aquacal.calibration.refinement as rf
import experiments.e1_refractive_comparison as e1  # noqa: E402
from aquacal.calibration._optim_common import build_bounds as _orig_build_bounds

GT_WATER_Z = None  # set at runtime from the scenario
EPS = 1e-9


def _pinned_build_bounds(
    camera_order,
    frame_order,
    reference_camera,
    base_intrinsics=None,
    refine_intrinsics=False,
    normal_fixed=True,
    shared_interface=True,
):
    lower, upper = _orig_build_bounds(
        camera_order,
        frame_order,
        reference_camera,
        base_intrinsics=base_intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
    )
    n_tilt = 0 if normal_fixed else 2
    n_ext = 6 * (len(camera_order) - 1)
    n_wz = 1 if shared_interface else len(camera_order)
    i = n_tilt + n_ext
    lower[i : i + n_wz] = GT_WATER_Z - EPS
    upper[i : i + n_wz] = GT_WATER_Z + EPS
    return lower, upper


def main():
    global GT_WATER_Z
    scenario = e1.create_scenario(e1.SCENARIO_NAME, seed=42)
    GT_WATER_Z = float(np.mean(list(scenario.water_zs.values())))
    print(f"pinning water_z = {GT_WATER_Z:.6f} m (ground truth), +/-{EPS}")

    ie.build_bounds = _pinned_build_bounds
    rf.build_bounds = _pinned_build_bounds

    results = {}
    for label, n_water in (("refractive", 1.333), ("non_refractive", 1.0)):
        print(f"\n--- {label} (n_water={n_water}) ---")
        res, det, timings, diag, discard = e1._run_one_model(scenario, n_water, 42)
        guard = discard.get("degenerate_observations_at_solution", 0)
        wz = float(np.mean([c.water_z for c in res.cameras.values()]))
        opt = diag["stage3_interface_optimization"].optimality
        print(f"  guard count           = {guard}")
        print(f"  final water_z         = {wz:.6f} m")
        print(f"  optimality (stage3)   = {opt:.3g}")
        results[label] = (res, det)

    print("\n=== depth sweep (pinned water_z) ===")
    dfs = e1._build_dataframes(scenario, results, seed=42)
    aniso = None
    for df in dfs if isinstance(dfs, (list, tuple)) else [dfs]:
        try:
            if {"test_depth_m", "z_rmse_mm", "model"} <= set(df.columns):
                aniso = df
        except AttributeError:
            continue
    if aniso is None:
        print("(could not locate anisotropy frame; dumping frames)")
        for i, df in enumerate(dfs):
            print(i, list(getattr(df, "columns", [])))
        return

    print(
        f"\n{'depth':>7} {'model':>16} {'xy_rmse_mm':>12} {'z_rmse_mm':>12} {'Z/XY':>8}"
    )
    for _, r in aniso.sort_values(["test_depth_m", "model"]).iterrows():
        print(
            f"{r['test_depth_m']:>7.1f} {r['model']:>16} "
            f"{r['xy_rmse_mm']:>12.4f} {r['z_rmse_mm']:>12.4f} "
            f"{r['anisotropy_ratio']:>8.3f}"
        )

    deep = aniso[aniso["test_depth_m"] == aniso["test_depth_m"].max()]
    nr = float(deep[deep["model"] == "non_refractive"]["z_rmse_mm"].iloc[0])
    rr = float(deep[deep["model"] == "refractive"]["z_rmse_mm"].iloc[0])
    print(f"\nDEEPEST-POINT RATIO (pinned): {nr:.1f} mm / {rr:.3f} mm = {nr / rr:.0f}x")
    print("  submitted paper: 257 mm / 1.9 mm = ~135x")
    print("  tonight (free) : 248.3 mm / 1.938 mm = ~128x")


if __name__ == "__main__":
    main()
