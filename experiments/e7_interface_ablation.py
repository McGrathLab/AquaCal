"""E7: shared-vs-per-camera interface ablation (EXP-05).

**The question this experiment answers.** Is AquaCal's shared-interface
parameterization (a single global `water_z` for the whole rig) a real
methodological contribution, or merely an engineering convenience that could
be replaced by letting each camera solve its own interface distance? This is
reviewer points R4.2 and R4.3.

**The primary result is the per-camera, fixed-intrinsics arm.** Naive
per-camera mode packs N free `water_z_i` parameters beside N free camera
centers `C_z_i`. Only the sum `C_z_i + d_i` (the absolute surface height) is
physically meaningful and must be identical across cameras -- but nothing in
that parameterization enforces it. The failure this arm demonstrates is a
**height/distance degeneracy** (`C_z_i <-> water_z_i`), never a focal-length
or standoff-distance failure: the intrinsics in this arm are held at ground
truth (see `INTRINSICS_FIXED_SOURCE` below), so there is no focal error to
propagate, and any scatter in recovered per-camera surface height is
attributable to the height/distance redundancy alone. This is deliberately
the *strongest possible case* for per-camera mode -- handed exact intrinsics,
the optimizer still scatters the recovered heights.

**Reprojection RMSE is a recorded control, never the headline.** A
height/distance degeneracy is a flat cost valley: every point along the
`C_z_i <-> water_z_i` trade-off reprojects equally well, so
`reprojection_rms_px_control` stays low in BOTH the shared and per-camera
arms. If RMSE also degraded sharply in the per-camera arm, the flat-valley
framing would need re-examining -- this is why the column is explicitly
suffixed `_control` rather than named as if it were evidence.

**The refine-ON arms are AquaCal's own rationale for importing intrinsics
from air, never "what CalibMar produces."** CalibMar solves each camera
independently in its own local frame and has no such redundancy -- it works
correctly in its intended regime. AquaCal's joint refractive bundle
adjustment is the reason importing Stage-1 in-air intrinsics (rather than
re-deriving them jointly) is the right default; the refine-ON arms here
measure AquaCal's own design choice, not a competing tool's behavior.

**What "ground-truth-fixed intrinsics" means (Pitfall 3 resolution).** The
two fixed-intrinsics arms hold intrinsics at `scenario.intrinsics` --
ground truth, not an independently-estimated in-air Stage-1 calibration.
This is the correct choice, not a shortcut: the primary result is a
geometric degeneracy in the extrinsics/interface parameterization, which
exists regardless of intrinsic accuracy. Perturbing the intrinsics would
inject a second, unrelated error source (focal error propagating into
recovered height) into the arm whose whole purpose is isolating the first
one. `INTRINSICS_FIXED_SOURCE` records this choice; `intrinsics_source` in
the emitted CSV records it per row so a reader of the data alone (not just
this docstring) learns what "fixed" meant.

Invoked as `python -m experiments.e7_interface_ablation`. Inherits the shared
five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`)
from `experiments._io.build_experiment_arg_parser` (D-21).

Emits, per D-17: `interface_ablation.csv` (one row per camera x arm),
`interface_ablation_conditioning.json` + `.npz` (per-arm conditioning,
interface spread, and height/distance correlation), one `e7_trace_<arm>.csv`
per arm, and one `e7_benchmark_<arm>.json` direct-call provenance record per
arm (D-09).

**D-19.3-11: this module RECORDS the final-solution guard count; it does
not GATE on it.** E7 has no per-arm `status` column -- each arm's
`e7_benchmark_<arm>.json` carries `problem_shape.
degenerate_observations_at_solution` (summed across `optimize_interface`'s
and, when `refine_intrinsics=True`, `joint_refinement`'s own
`discard_stats_out` sinks), and a non-zero count logs one prominent warning
naming the arm and the count. The pass/fail decision, when one is needed,
belongs to plan 19.3-08's queue script. `--smoke`'s `"minimal"` scenario
(`create_scenario("minimal", ...)` above) legitimately reports a non-zero
count (extreme obliquity, not a breached interface, see
`19.3-ORCHESTRATOR-NOTES.md` section 4); nothing in this module compares the
count to anything, so that number can never become an exit code.
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

from aquacal.calibration import build_interface_spread_report
from aquacal.calibration._observability import OptimizerObserver, SolverDiagnostics
from aquacal.calibration.extrinsics import build_pose_graph, estimate_extrinsics
from aquacal.calibration.interface_estimation import optimize_interface
from aquacal.calibration.refinement import joint_refinement
from aquacal.core.board import BoardGeometry
from aquacal.datasets import create_scenario, generate_synthetic_detections
from aquacal.validation.conditioning import save_conditioning_report
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    exit_code_for,
    resolve_out_dir,
    validate_args,
    write_direct_call_benchmark,
    write_experiment_csv,
)

logger = logging.getLogger(__name__)

# Four arms: (arm_name, shared_interface, refine_intrinsics). Identical
# scenario/noise/target/seed/initial_water_zs across all four (D-17) -- only
# these two booleans vary per arm.
ARMS: list[tuple[str, bool, bool]] = [
    ("shared_fixed", True, False),
    ("shared_refined", True, True),
    ("percamera_fixed", False, False),
    ("percamera_refined", False, True),
]
PRIMARY_ARM = "percamera_fixed"

# Pitfall 3 resolution: the fixed-intrinsics arms use ground-truth intrinsics,
# not an independently-estimated in-air calibration. This isolates the
# height/distance degeneracy from any confound of intrinsic error and makes
# the per-camera arm the strongest possible case for per-camera mode. See the
# module docstring's "ground-truth-fixed intrinsics" section for the full
# reasoning -- a code-reading reviewer will check this constant and the
# `intrinsics_source` CSV column, not only the prose.
INTRINSICS_FIXED_SOURCE = "ground_truth"

CHECK_RTOL = 1e-6
ABLATION_KEY_COLUMNS = ["arm", "camera"]
REFERENCE_CAMERA = "cam0"
INTERFACE_NORMAL = np.array([0.0, 0.0, -1.0], dtype=np.float64)

ABLATION_COLUMNS = [
    "arm",
    "shared_interface",
    "refine_intrinsics",
    "intrinsics_source",
    "camera",
    "water_z_recovered_m",
    "water_z_gt_m",
    "water_z_error_mm",
    "camera_height_recovered_m",
    "camera_height_gt_m",
    "camera_height_drift_mm",
    "surface_height_sum_m",
    "focal_length_recovered_px",
    "focal_length_gt_px",
    "focal_drift_pct",
    "standoff_m",
    "reprojection_rms_px_control",
]

STAGE_INTERFACE = "stage3_interface_optimization"
STAGE_INTRINSIC_PASS = "stage3_intrinsic_pass"


class ArmResult:
    """Everything produced by running one ablation arm to completion."""

    def __init__(
        self,
        arm_name: str,
        shared_interface: bool,
        refine_intrinsics: bool,
        extrinsics: dict,
        water_zs: dict,
        intrinsics: dict,
        rms: float,
        diagnostics: dict[str, SolverDiagnostics],
        observers: dict[str, OptimizerObserver],
        elapsed_seconds: dict[str, float],
        degenerate_observations_at_solution: int = 0,
    ) -> None:
        self.arm_name = arm_name
        self.shared_interface = shared_interface
        self.refine_intrinsics = refine_intrinsics
        self.extrinsics = extrinsics
        self.water_zs = water_zs
        self.intrinsics = intrinsics
        self.rms = rms
        self.diagnostics = diagnostics
        self.observers = observers
        self.elapsed_seconds = elapsed_seconds
        # D-19.3-11/plan 19.3-07: the final-solution guard count, SUMMED
        # across this arm's stages (Stage 3, and Stage 3's intrinsic pass
        # when refine_intrinsics=True) -- a per-arm question ("did degeneracy
        # occur anywhere in this arm's solve"), matching plan 19.3-02's own
        # whole-run-summed convention for this same key.
        self.degenerate_observations_at_solution = degenerate_observations_at_solution

    @property
    def intrinsics_source(self) -> str:
        """What "fixed"/"refined" meant for this arm (Pitfall 3 resolution)."""
        return (
            "refined_from_ground_truth"
            if self.refine_intrinsics
            else "ground_truth_fixed"
        )

    @property
    def final_stage(self) -> str:
        """The last stage that ran for this arm."""
        return STAGE_INTRINSIC_PASS if self.refine_intrinsics else STAGE_INTERFACE


def _build_shared_data(seed: int, smoke: bool):
    """Build the ONE scenario/detections/Stage-2 result shared by all four arms.

    Constructed exactly once (RESEARCH E7 mechanics point 5) so any difference
    between arms is attributable to the ablation variable (`shared_interface`,
    `refine_intrinsics`) and nothing else -- not to different detections,
    different Stage-2 poses, or different starting guesses.
    """
    scenario_name = "minimal" if smoke else "realistic"
    scenario = create_scenario(scenario_name, seed=seed, n_air=1.0, n_water=1.333)
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
        seed=seed,
    )
    pose_graph = build_pose_graph(detections, min_cameras=2)
    # Refraction-aware Stage 2, mirroring calibrate_synthetic's pattern
    # (pipelines.py) -- omitting water_zs/interface_normal/n_air/n_water here
    # would silently degrade the initial extrinsics guess for a refractive
    # scenario, which is a Stage-2 problem unrelated to the ablation variable
    # and would confound shared-vs-per-camera convergence comparisons.
    initial_extrinsics = estimate_extrinsics(
        pose_graph,
        scenario.intrinsics,
        board,
        REFERENCE_CAMERA,
        water_zs=scenario.water_zs,
        interface_normal=INTERFACE_NORMAL,
        n_air=scenario.n_air,
        n_water=scenario.n_water,
    )
    # A fixed, deterministic seed dict -- not re-drawn per arm (RESEARCH E7
    # mechanics point 5) -- the ground-truth surface height, matching
    # calibrate_synthetic's own initial_water_zs seeding pattern so all four
    # arms start from the same physically plausible guess.
    initial_water_zs = dict(scenario.water_zs)
    return scenario, board, detections, initial_extrinsics, initial_water_zs


def _run_arm(
    arm_name: str,
    shared_interface: bool,
    refine_intrinsics: bool,
    scenario,
    board,
    detections,
    initial_extrinsics,
    initial_water_zs,
) -> ArmResult:
    """Run one ablation arm: Stage 3, then optionally Stage 3's intrinsic pass.

    Constructs one fresh `SolverDiagnostics` and one conditioning-enabled
    `OptimizerObserver` per stage, passed as `diagnostics_out=`/`observer=`.
    This function does not replicate the observer's internal parameter-layout
    wiring itself -- `optimize_interface`/`joint_refinement` already do that
    internally (RESEARCH E7 mechanics point 2). `ConditioningMemoryError` is
    never caught here: if `on_solution` raises it, it propagates all the way
    out, exactly as its docstring requires (RESEARCH E7 mechanics point 3).
    """
    diagnostics: dict[str, SolverDiagnostics] = {}
    observers: dict[str, OptimizerObserver] = {}
    elapsed_seconds: dict[str, float] = {}

    diag_stage3 = SolverDiagnostics()
    observer_stage3 = OptimizerObserver(stage=STAGE_INTERFACE, conditioning=True)
    discard_stats_stage3: dict[str, int] = {}

    t0 = time.perf_counter()
    ext, dist, poses, rms = optimize_interface(
        detections=detections,
        intrinsics=scenario.intrinsics,
        initial_extrinsics=initial_extrinsics,
        board=board,
        reference_camera=REFERENCE_CAMERA,
        initial_water_zs=initial_water_zs,
        interface_normal=INTERFACE_NORMAL,
        n_air=scenario.n_air,
        n_water=scenario.n_water,
        loss="huber",
        loss_scale=1.0,
        min_corners=4,
        verbose=0,
        shared_interface=shared_interface,
        observer=observer_stage3,
        diagnostics_out=diag_stage3,
        discard_stats_out=discard_stats_stage3,
    )
    elapsed_seconds[STAGE_INTERFACE] = time.perf_counter() - t0
    diagnostics[STAGE_INTERFACE] = diag_stage3
    observers[STAGE_INTERFACE] = observer_stage3
    n_degenerate = discard_stats_stage3.get("degenerate_observations_at_solution", 0)

    intrinsics_final = scenario.intrinsics
    if refine_intrinsics:
        diag_intrinsic_pass = SolverDiagnostics()
        observer_intrinsic_pass = OptimizerObserver(
            stage=STAGE_INTRINSIC_PASS, conditioning=True
        )
        discard_stats_intrinsic_pass: dict[str, int] = {}
        t1 = time.perf_counter()
        ext, dist, poses, intrinsics_final, rms = joint_refinement(
            stage3_result=(ext, dist, poses, rms),
            detections=detections,
            intrinsics=scenario.intrinsics,
            board=board,
            reference_camera=REFERENCE_CAMERA,
            refine_intrinsics=True,
            interface_normal=INTERFACE_NORMAL,
            n_air=scenario.n_air,
            n_water=scenario.n_water,
            loss="huber",
            loss_scale=1.0,
            min_corners=4,
            verbose=0,
            shared_interface=shared_interface,
            observer=observer_intrinsic_pass,
            diagnostics_out=diag_intrinsic_pass,
            discard_stats_out=discard_stats_intrinsic_pass,
        )
        elapsed_seconds[STAGE_INTRINSIC_PASS] = time.perf_counter() - t1
        diagnostics[STAGE_INTRINSIC_PASS] = diag_intrinsic_pass
        observers[STAGE_INTRINSIC_PASS] = observer_intrinsic_pass
        n_degenerate += discard_stats_intrinsic_pass.get(
            "degenerate_observations_at_solution", 0
        )

    if n_degenerate > 0:
        # D-19.3-11: recorded and warned about, never gated -- E7 has no
        # per-arm status column (see the module docstring's RECORDS/GATES
        # note); plan 19.3-08's queue script owns any pass/fail decision.
        logger.warning(
            "arm=%s: %d degenerate observation(s) recorded at the final "
            "solution -- first-order optimality is unreliable for this arm "
            "(D-19.3-11).",
            arm_name,
            n_degenerate,
        )

    return ArmResult(
        arm_name=arm_name,
        shared_interface=shared_interface,
        refine_intrinsics=refine_intrinsics,
        extrinsics=ext,
        water_zs=dist,
        intrinsics=intrinsics_final,
        rms=rms,
        diagnostics=diagnostics,
        observers=observers,
        elapsed_seconds=elapsed_seconds,
        degenerate_observations_at_solution=n_degenerate,
    )


def _build_ablation_rows(arm: ArmResult, scenario) -> list[dict]:
    """Build one `interface_ablation.csv` row per camera for one arm.

    `camera_height_*` is `water_z - C_z` (the physical camera-to-water gap,
    CLAUDE.md convention), meters. `surface_height_sum_m` is `C_z + d` -- the
    physically meaningful quantity that must be common to all cameras; its
    scatter across cameras within an arm IS the primary height/distance
    result. `standoff_m` is the same physical camera-to-water gap, named for
    its role pairing against `focal_drift_pct` in the refine-ON arms'
    conditioning correlation block -- it is never itself named a degeneracy.
    """
    rows = []
    for cam in sorted(scenario.intrinsics):
        water_z_recovered = float(arm.water_zs[cam])
        water_z_gt = float(scenario.water_zs[cam])
        C_z_recovered = float(arm.extrinsics[cam].C[2])
        C_z_gt = float(scenario.extrinsics[cam].C[2])

        camera_height_recovered = water_z_recovered - C_z_recovered
        camera_height_gt = water_z_gt - C_z_gt
        surface_height_sum = C_z_recovered + camera_height_recovered

        fx_recovered = float(arm.intrinsics[cam].K[0, 0])
        fx_gt = float(scenario.intrinsics[cam].K[0, 0])
        focal_drift_pct = (fx_recovered - fx_gt) / fx_gt * 100.0

        rows.append(
            {
                "arm": arm.arm_name,
                "shared_interface": arm.shared_interface,
                "refine_intrinsics": arm.refine_intrinsics,
                "intrinsics_source": arm.intrinsics_source,
                "camera": cam,
                "water_z_recovered_m": water_z_recovered,
                "water_z_gt_m": water_z_gt,
                "water_z_error_mm": (water_z_recovered - water_z_gt) * 1000.0,
                "camera_height_recovered_m": camera_height_recovered,
                "camera_height_gt_m": camera_height_gt,
                "camera_height_drift_mm": (camera_height_recovered - camera_height_gt)
                * 1000.0,
                "surface_height_sum_m": surface_height_sum,
                "focal_length_recovered_px": fx_recovered,
                "focal_length_gt_px": fx_gt,
                "focal_drift_pct": focal_drift_pct,
                "standoff_m": camera_height_recovered,
                "reprojection_rms_px_control": float(arm.rms),
            }
        )
    return rows


def _water_z_label(cam: str, shared_interface: bool) -> str:
    return "water_z" if shared_interface else f"{cam}_water_z"


def _pairwise_correlations(report, pairs: list[tuple[str, str]]) -> dict[str, float]:
    """Select named entries out of a `ConditioningReport.correlation` matrix."""
    if report.parameter_names is None:
        return {}
    index = {name: i for i, name in enumerate(report.parameter_names)}
    out: dict[str, float] = {}
    for label, (a, b) in pairs:
        if a in index and b in index:
            out[label] = float(report.correlation[index[a], index[b]])
    return out


def _build_conditioning_entry(
    arm: ArmResult, scenario, tmp_dir: Path, npz_arrays: dict
) -> dict:
    """Build one arm's `per_arm` conditioning entry, reusing the library's own
    serialization (`save_conditioning_report`) rather than hand-rolling one.

    Writes each stage's report to per-arm-stage scratch files under `tmp_dir`,
    reads the JSON scalars/spectrum back, and stashes the `(n, n)` correlation
    matrix into `npz_arrays` (the caller writes ONE combined NPZ at the end --
    the matrix itself is never serialized to JSON, per
    `save_conditioning_report`'s own contract).
    """
    camera_order = sorted(scenario.intrinsics)
    stage_payloads: dict[str, dict] = {}

    for stage_name, observer in arm.observers.items():
        report = observer.conditioning_report
        if report is None:
            continue
        arm_stage = f"{arm.arm_name}_{stage_name}"
        tmp_json = tmp_dir / f"{arm_stage}.json"
        tmp_npz = tmp_dir / f"{arm_stage}.npz"
        save_conditioning_report(report, tmp_json, tmp_npz, stage=arm_stage)
        with open(tmp_json) as f:
            payload = json.load(f)
        stage_payloads[stage_name] = payload
        npz_arrays[f"{arm_stage}_correlation"] = report.correlation
        npz_arrays[f"{arm_stage}_singular_values"] = report.singular_values

    # The arm's headline scalars/spectrum come from its FINAL stage's report
    # -- the converged state after every parameter this arm touches has been
    # optimized.
    final_report = arm.observers[arm.final_stage].conditioning_report
    entry = dict(stage_payloads[arm.final_stage])

    height_distance_pairs = [
        (
            cam,
            (
                f"{cam}_tvec_z",
                _water_z_label(cam, arm.shared_interface),
            ),
        )
        for cam in camera_order
        if cam != REFERENCE_CAMERA
    ]
    entry["height_distance_correlation"] = _pairwise_correlations(
        final_report, height_distance_pairs
    )

    if arm.refine_intrinsics:
        intrinsic_report = arm.observers[STAGE_INTRINSIC_PASS].conditioning_report
        focal_standoff_pairs = [
            (cam, (f"{cam}_fx", f"{cam}_tvec_z"))
            for cam in camera_order
            if cam != REFERENCE_CAMERA
        ]
        entry["focal_standoff_correlation"] = _pairwise_correlations(
            intrinsic_report, focal_standoff_pairs
        )

    entry["interface_spread"] = build_interface_spread_report(
        {cam: arm.water_zs[cam] for cam in camera_order}, stage=arm.arm_name
    )
    return entry


def _write_ablation_artifacts(
    results: list[ArmResult], scenario, out_dir: Path, force: bool
) -> None:
    """Emit the full D-17 file set: CSV, conditioning JSON/NPZ, traces, benchmarks."""
    all_rows: list[dict] = []
    for arm in results:
        all_rows.extend(_build_ablation_rows(arm, scenario))
    df = pd.DataFrame(all_rows, columns=ABLATION_COLUMNS)
    write_experiment_csv(
        df,
        out_dir / "interface_ablation.csv",
        key_columns=ABLATION_KEY_COLUMNS,
        force=force,
    )

    with tempfile.TemporaryDirectory(prefix="e7_conditioning_") as tmp:
        tmp_dir = Path(tmp)
        npz_arrays: dict = {}
        per_arm = {}
        for arm in results:
            per_arm[arm.arm_name] = _build_conditioning_entry(
                arm, scenario, tmp_dir, npz_arrays
            )

        conditioning_json_path = out_dir / "interface_ablation_conditioning.json"
        conditioning_npz_path = out_dir / "interface_ablation_conditioning.npz"
        if force or not conditioning_json_path.exists():
            with open(conditioning_json_path, "w") as f:
                json.dump({"per_arm": per_arm}, f, indent=2, sort_keys=True)
        if force or not conditioning_npz_path.exists():
            np.savez_compressed(conditioning_npz_path, **npz_arrays)

    for arm in results:
        trace_path = out_dir / f"e7_trace_{arm.arm_name}.csv"
        if force or not trace_path.exists():
            arm.observers[arm.final_stage].write_trace_csv(trace_path)

    for arm in results:
        problem_shape = {
            "n_cameras": len(scenario.intrinsics),
            "n_frames_calibration": len(scenario.board_poses),
            "n_frames_holdout": 0,
            # D-19.3-11: this arm's final-solution guard count, summed across
            # its stages (recorded, never gated -- see the module docstring).
            "degenerate_observations_at_solution": (
                arm.degenerate_observations_at_solution
            ),
        }
        solver_config = {
            "robust_loss": "huber",
            "loss_scale": 1.0,
            "refine_intrinsics": arm.refine_intrinsics,
            "shared_interface": arm.shared_interface,
            "n_water": scenario.n_water,
            "n_air": scenario.n_air,
        }
        final_diag = arm.diagnostics[arm.final_stage]
        solver_config["ftol"] = final_diag.ftol
        solver_config["xtol"] = final_diag.xtol
        solver_config["gtol"] = final_diag.gtol
        accuracy = {"reprojection_rms_px": float(arm.rms)}
        write_direct_call_benchmark(
            out_dir / f"e7_benchmark_{arm.arm_name}.json",
            problem_shape=problem_shape,
            timings=arm.elapsed_seconds,
            diagnostics=arm.diagnostics,
            solver_config=solver_config,
            accuracy=accuracy,
            force=force,
        )


def run_all_arms(seed: int, smoke: bool) -> tuple[list[ArmResult], object]:
    """Build the shared data once and run all four arms against it."""
    scenario, board, detections, initial_extrinsics, initial_water_zs = (
        _build_shared_data(seed, smoke)
    )
    results = []
    for arm_name, shared_interface, refine_intrinsics in ARMS:
        logger.info("Running arm %s...", arm_name)
        results.append(
            _run_arm(
                arm_name,
                shared_interface,
                refine_intrinsics,
                scenario,
                board,
                detections,
                initial_extrinsics,
                initial_water_zs,
            )
        )
    return results, scenario


def _log_smoke_summary(results: list[ArmResult]) -> None:
    """Log a one-line-per-arm summary naming all four arms (smoke visibility)."""
    for arm in results:
        logger.info(
            "  arm=%s shared_interface=%s refine_intrinsics=%s rms=%.4f",
            arm.arm_name,
            arm.shared_interface,
            arm.refine_intrinsics,
            arm.rms,
        )


def _run_check(out_dir: Path) -> int:
    """`--check`: compare a fresh run against the committed `interface_ablation.csv`."""
    committed_path = out_dir / "interface_ablation.csv"
    if not committed_path.exists():
        print(f"No committed baseline at {committed_path} to check against.")
        return 1
    results, scenario = run_all_arms(seed=42, smoke=False)
    all_rows: list[dict] = []
    for arm in results:
        all_rows.extend(_build_ablation_rows(arm, scenario))
    fresh = pd.DataFrame(all_rows, columns=ABLATION_COLUMNS)
    report = compare_experiment_csv(
        fresh, committed_path, key_columns=ABLATION_KEY_COLUMNS, rtol=CHECK_RTOL
    )
    print(report.message)
    return exit_code_for(report)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E7's CLI parser, extending the shared five-flag contract (D-21)."""
    return argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e7_interface_ablation`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        out_dir = resolve_out_dir(args.out)
        return _run_check(out_dir)

    if args.smoke:
        # Honor an explicitly-passed --out (e.g. a caller-supplied temp dir
        # for verification); otherwise fall back to a throwaway temp
        # directory so a bare `--smoke` never pollutes the real
        # experiments/results output.
        if args.out == parser.get_default("out"):
            with tempfile.TemporaryDirectory(prefix="e7_smoke_") as tmp:
                out_dir = resolve_out_dir(Path(tmp))
                results, scenario = run_all_arms(seed=args.seed, smoke=True)
                _log_smoke_summary(results)
                _write_ablation_artifacts(results, scenario, out_dir, force=True)
        else:
            out_dir = resolve_out_dir(args.out)
            results, scenario = run_all_arms(seed=args.seed, smoke=True)
            _log_smoke_summary(results)
            _write_ablation_artifacts(results, scenario, out_dir, force=True)
        return 0

    out_dir = resolve_out_dir(args.out)
    results, scenario = run_all_arms(seed=args.seed, smoke=False)
    _write_ablation_artifacts(results, scenario, out_dir, force=args.force)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
