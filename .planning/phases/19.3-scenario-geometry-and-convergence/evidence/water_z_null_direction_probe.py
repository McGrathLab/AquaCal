"""
Diagnostic probe: is water_z a structural null direction at n_water = 1.0?

If it is, then E1's non-refractive arm's 14,949 degenerate-observation count is
bookkeeping with no numerical consequence for the fitted cameras, and the paper's
refractive-vs-non-refractive comparison is unaffected by the 7e0cb90 guard.

Null-direction-ness is a property of the RESIDUAL FUNCTION, not of any particular
solution, so this evaluates at ground truth -- no calibration required.

Test: hold every parameter fixed, vary water_z, compare residual vectors.
  n_water = 1.0    -> expected BIT-IDENTICAL (null direction)
  n_water = 1.333  -> control; must NOT be identical, else the probe is blind.

Read-only with respect to the repo.
"""

import numpy as np

from aquacal.calibration._optim_common import compute_residuals, pack_params
from aquacal.core.board import BoardGeometry
from aquacal.datasets import create_scenario, generate_synthetic_detections

SEED = 42
INTERFACE_NORMAL = np.array([0.0, 0.0, -1.0])


def probe(n_water, label):
    print(f"\n{'=' * 72}\n  {label}   (n_water = {n_water})\n{'=' * 72}")

    scenario = create_scenario("realistic", seed=SEED)
    board = BoardGeometry(scenario.board_config)
    detections = generate_synthetic_detections(
        intrinsics=scenario.intrinsics,
        extrinsics=scenario.extrinsics,
        water_zs=scenario.water_zs,
        board=board,
        board_poses=scenario.board_poses,
        noise_std=scenario.noise_std,
        n_air=scenario.n_air,
        n_water=scenario.n_water,
        seed=SEED,
    )

    camera_order = sorted(scenario.extrinsics)
    reference_camera = next(
        (
            n
            for n, e in scenario.extrinsics.items()
            if np.allclose(e.t, 0) and np.allclose(e.R, np.eye(3))
        ),
        camera_order[0],
    )
    board_poses = {p.frame_idx: p for p in scenario.board_poses}
    frame_order = sorted(board_poses)

    z0 = float(np.mean(list(scenario.water_zs.values())))
    print(f"ground-truth water_z = {z0:.6f} m")
    print(f"cameras = {len(camera_order)}, frames = {len(frame_order)}")

    def residuals_at(z):
        params = pack_params(
            extrinsics=scenario.extrinsics,
            water_z=z,
            board_poses=board_poses,
            reference_camera=reference_camera,
            camera_order=camera_order,
            frame_order=frame_order,
            intrinsics=scenario.intrinsics,
            refine_intrinsics=False,
            normal_fixed=True,
            shared_interface=True,
        )
        counts = []
        r = compute_residuals(
            params=params,
            detections=detections,
            base_intrinsics=scenario.intrinsics,
            board=board,
            reference_camera=reference_camera,
            reference_extrinsics=scenario.extrinsics[reference_camera],
            interface_normal=INTERFACE_NORMAL,
            n_air=1.0,
            n_water=n_water,
            camera_order=camera_order,
            frame_order=frame_order,
            min_corners=4,
            refine_intrinsics=False,
            normal_fixed=True,
            shared_interface=True,
            invalid_count_out=counts,
        )
        return r, (counts[0] if counts else 0)

    base = None
    print(
        f"\n{'water_z (m)':>12} {'guard count':>12} {'cost':>16} {'residual vs base':>26}"
    )
    for d in [0.0, -0.5, -0.2, -0.05, +0.05, +0.2, +0.5, +1.0]:
        r, cnt = residuals_at(z0 + d)
        cost = 0.5 * float(np.sum(r**2))
        if base is None:
            base, verdict = r, "(base)"
        elif r.shape != base.shape:
            verdict = f"SHAPE {r.shape} vs {base.shape}"
        elif np.array_equal(r, base):
            verdict = "BIT-IDENTICAL"
        else:
            verdict = f"differs, max|d|={np.max(np.abs(r - base)):.3e}"
        print(f"{z0 + d:>12.4f} {cnt:>12d} {cost:>16.8f} {verdict:>26}")


if __name__ == "__main__":
    probe(1.0, "NON-REFRACTIVE ARM  (the paper's pinhole baseline)")
    probe(1.333, "REFRACTIVE CONTROL  (probe must detect dependence here)")
