"""Unit tests for E3 tiers 1-3 (D-22, D-18, D-21, EXP-07).

Fast unit tests -- minimal fixtures constructed directly, no `create_scenario`, no calibration,
none marked slow.

Adapts (does not import) `_make_detections`/`_make_pattern`/`_make_extrinsics`/`_make_board_poses`
from `tests/unit/test_optim_common.py` so this file stands alone.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from aquacal.calibration._optim_common import (
    build_jacobian_sparsity,
    build_structural_column_groups,
    pack_params,
)
from aquacal.config.schema import (
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    Detection,
    DetectionResult,
    FrameDetections,
)


def _make_detections(n_cams, n_frames, visibility, corners_per_view=4, seed=0):
    """Build a DetectionResult where each camera sees each frame with prob `visibility`.

    At least one camera is guaranteed per frame so no frame is empty. Adapted from
    `tests/unit/test_optim_common.py`.
    """
    rng = np.random.default_rng(seed)
    camera_names = [f"cam{i}" for i in range(n_cams)]
    corner_ids = np.arange(corners_per_view, dtype=np.int32)

    frames = {}
    for frame_idx in range(n_frames):
        visible = [c for c in camera_names if rng.random() < visibility]
        if not visible:
            visible = [camera_names[rng.integers(n_cams)]]

        detections = {
            cam: Detection(
                corner_ids=corner_ids.copy(),
                corners_2d=rng.uniform(0.0, 1000.0, size=(corners_per_view, 2)),
            )
            for cam in visible
        }
        frames[frame_idx] = FrameDetections(frame_idx=frame_idx, detections=detections)

    return DetectionResult(
        frames=frames,
        camera_names=camera_names,
        total_frames=n_frames,
    )


def _make_pattern(
    n_cams,
    n_frames,
    visibility,
    refine_intrinsics,
    normal_fixed,
    shared_interface=True,
    seed=0,
):
    """Build a board-observation sparsity pattern for the given configuration."""
    detections = _make_detections(n_cams, n_frames, visibility, seed=seed)
    return build_jacobian_sparsity(
        detections,
        reference_camera="cam0",
        camera_order=[f"cam{i}" for i in range(n_cams)],
        frame_order=list(range(n_frames)),
        min_corners=1,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
    )


def _make_extrinsics(camera_order):
    """Build a per-camera extrinsics dict with distinct translations."""
    rng = np.random.default_rng(1)
    return {
        cam: CameraExtrinsics(R=np.eye(3), t=rng.normal(size=3)) for cam in camera_order
    }


def _make_board_poses(frame_order):
    """Build a per-frame board-pose dict with distinct rvec/tvec."""
    rng = np.random.default_rng(2)
    return {
        f: BoardPose(frame_idx=f, rvec=rng.normal(size=3), tvec=rng.normal(size=3))
        for f in frame_order
    }


def _make_intrinsics(camera_order):
    """Build a per-camera intrinsics dict, only needed when refine_intrinsics=True."""
    K = np.array([[500.0, 0, 320], [0, 500.0, 240], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros(5, dtype=np.float64)
    return {
        cam: CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        )
        for cam in camera_order
    }


def expected_P(
    n_cams, n_frames, refine_intrinsics, normal_fixed, shared_interface=True
):
    """Closed-form parameter count `P`, mirroring `pack_params`' block layout.

    Each term below was verified against `pack_params`' body (`_optim_common.py`), not copied
    from the supplement on faith:
    - `2` reference-camera tilt params (rx, ry) when `not normal_fixed`, else `0`.
    - `6 * (n_cams - 1)` extrinsic params: one (rvec(3), tvec(3)) block per non-reference
      camera in `camera_order`.
    - `1` water_z param when `shared_interface`, else `n_cams` (one per camera, reference
      included).
    - `6 * n_frames` board-pose params: one (rvec(3), tvec(3)) block per frame.
    - `4 * n_cams` intrinsic params (fx, fy, cx, cy per camera) when `refine_intrinsics`,
      else `0`.
    """
    tilt = 0 if normal_fixed else 2
    extrinsics = 6 * (n_cams - 1)
    water_z = 1 if shared_interface else n_cams
    poses = 6 * n_frames
    intrinsics = 4 * n_cams if refine_intrinsics else 0
    return tilt + extrinsics + water_z + poses + intrinsics


# (n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface). Six configurations
# spanning two rig sizes and all three boolean axes (D-22).
_CONFIGS = [
    (3, 4, True, False, True),
    (3, 4, False, True, True),
    (3, 4, True, False, False),
    (5, 6, False, False, True),
    (5, 6, True, True, True),
    (5, 6, False, True, False),
]


def _pack_params_for_config(
    n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
):
    camera_order = [f"cam{i}" for i in range(n_cams)]
    frame_order = list(range(n_frames))
    extrinsics = _make_extrinsics(camera_order)
    board_poses = _make_board_poses(frame_order)
    intrinsics = _make_intrinsics(camera_order) if refine_intrinsics else None
    water_z_per_camera = (
        None
        if shared_interface
        else {cam: 0.15 + 0.01 * i for i, cam in enumerate(camera_order)}
    )
    return pack_params(
        extrinsics,
        0.15,
        board_poses,
        reference_camera="cam0",
        camera_order=camera_order,
        frame_order=frame_order,
        intrinsics=intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
        water_z_per_camera=water_z_per_camera,
    )


class TestPackParamsLengthMatchesLibrary:
    """`pytest -k pack_params` selects both configuration sweeps (D-22)."""

    @pytest.mark.parametrize(
        "n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface", _CONFIGS
    )
    def test_pack_params_length_matches_sparsity_columns(
        self, n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
    ):
        """`len(pack_params(...))` equals `build_jacobian_sparsity(...).shape[1]`."""
        params = _pack_params_for_config(
            n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
        )
        S = _make_pattern(
            n_cams,
            n_frames,
            visibility=1.0,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )
        assert len(params) == S.shape[1]

    @pytest.mark.parametrize(
        "n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface", _CONFIGS
    )
    def test_pack_params_length_matches_closed_form(
        self, n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
    ):
        """`len(pack_params(...))` equals the closed-form `expected_P`, restating the
        supplement's formula in code and validating it against the live packer rather than
        trusting the arithmetic."""
        params = _pack_params_for_config(
            n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
        )
        assert len(params) == expected_P(
            n_cams, n_frames, refine_intrinsics, normal_fixed, shared_interface
        )


class TestPerCameraModeGrowsPWithoutGrowingGroups:
    """D-21's prediction, confirmed by measurement rather than assumed."""

    def test_per_camera_mode_grows_p_without_growing_groups(self):
        n_cams, n_frames = 4, 5
        normal_fixed, refine_intrinsics = True, False

        S_shared = _make_pattern(
            n_cams,
            n_frames,
            visibility=1.0,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=True,
        )
        S_pc = _make_pattern(
            n_cams,
            n_frames,
            visibility=1.0,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=False,
        )

        # P strictly grows: N per-camera water_z columns replace the single shared column.
        assert S_pc.shape[1] > S_shared.shape[1]
        assert S_pc.shape[1] - S_shared.shape[1] == n_cams - 1

        groups_shared = build_structural_column_groups(
            S_shared,
            n_cams,
            n_frames,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=True,
        )
        groups_pc = build_structural_column_groups(
            S_pc,
            n_cams,
            n_frames,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=False,
        )

        # Group count unchanged: two cameras' water_z columns never share a residual row, so
        # they collapse into the same FD group slot the shared water_z column occupied.
        assert groups_pc.max() + 1 == groups_shared.max() + 1


# --- E3 tier 1 / tier 3 / sidecar behaviors (Task 3) -----------------------------------

BENCHMARK_JSON_PATH = (
    Path(__file__).resolve().parents[2] / "experiments" / "results" / "benchmark.json"
)

# The six published `tab:cpr` configurations (19.2-SOURCE-BRIEF.md Sec E3 Tier 3), as
# (n_cameras, n_frames, normal_fixed, refine_intrinsics) tuples. Every row is
# normal_fixed=False (tilt-enabled) -- a tilt-fixed row would report a P exactly 2 smaller
# and look entirely plausible (review H1).
_EXPECTED_TAB_CPR_CONFIGS = {
    (3, 3, False, False),
    (16, 200, False, False),
    (8, 100, False, True),
    (12, 100, False, True),
    (13, 200, False, True),
    (16, 200, False, True),
}


class TestBuildCodeConstantsDfShape:
    """`test_build_code_constants_df_shape` (Task 3 behavior 1)."""

    def test_build_code_constants_df_shape(self):
        from experiments.e3_derived_quantities import (
            CODE_CONSTANTS_COLUMNS,
            build_code_constants_df,
        )

        df = build_code_constants_df()
        assert list(df.columns) == CODE_CONSTANTS_COLUMNS
        assert len(df.columns) == 7
        assert len(df) == 9  # len(DECLARED_CONSTANTS), plan 04's M10 fix
        assert set(df["pass_fail"]) <= {"PASS", "FAIL"}


class TestCPRConfigsCoverAllSixTabCprRows:
    """`test_cpr_configs_cover_all_six_tab_cpr_rows` (Task 3 behavior 2, retires D-16 split)."""

    def test_cpr_configs_cover_all_six_tab_cpr_rows(self):
        from experiments.e3_derived_quantities import CPR_CONFIGS

        assert set(CPR_CONFIGS) == _EXPECTED_TAB_CPR_CONFIGS
        assert len(CPR_CONFIGS) == 6


class TestCPRConfigsAreAllTiltEnabled:
    """`test_cpr_configs_are_all_tilt_enabled` (Task 3 behavior 3)."""

    def test_cpr_configs_are_all_tilt_enabled(self):
        from experiments.e3_derived_quantities import CPR_CONFIGS

        for n_cameras, n_frames, normal_fixed, refine_intrinsics in CPR_CONFIGS:
            assert normal_fixed is False


class TestCPRRowBuilderShape:
    """`test_cpr_row_builder_shape` (Task 3 behavior 4)."""

    def test_cpr_row_builder_shape(self):
        from experiments.e3_derived_quantities import (
            CPR_COLUMNS,
            _build_computed_cpr_row,
        )

        row = _build_computed_cpr_row(
            config_key="tiny_test_config",
            n_cameras=3,
            n_frames=2,
            normal_fixed=False,
            refine_intrinsics=False,
            shared_interface=True,
        )
        assert set(row.keys()) == set(CPR_COLUMNS)
        assert row["n_params"] > 0
        assert row["n_groups"] > 0
        assert row["fd_reduction"] == pytest.approx(row["n_params"] / row["n_groups"])
        assert row["record_source"] == "computed"


class TestPerCameraRowsPresent:
    """`test_per_camera_rows_present` (Task 3 behavior 5)."""

    def test_per_camera_rows_present(self):
        from experiments.e3_derived_quantities import build_cpr_grouping_df

        df = build_cpr_grouping_df(BENCHMARK_JSON_PATH)
        key_cols = ["n_cameras", "n_frames", "refine_intrinsics", "normal_fixed"]

        shared_keys = set(
            map(tuple, df[df["shared_interface"]][key_cols].to_numpy().tolist())
        )
        percamera_keys = set(
            map(tuple, df[~df["shared_interface"]][key_cols].to_numpy().tolist())
        )
        assert shared_keys == percamera_keys
        assert len(shared_keys) == 6


class TestLatexFragmentDefaultExcludesPerCamera:
    """`test_latex_fragment_default_excludes_per_camera` (Task 3 behavior 6, D-21)."""

    def test_latex_fragment_default_excludes_per_camera(self):
        from experiments.e3_derived_quantities import _select_cpr_rows_for_latex

        df = pd.DataFrame(
            [
                {"config_key": "a_shared", "shared_interface": True},
                {"config_key": "a_percamera", "shared_interface": False},
            ]
        )

        default_selection = _select_cpr_rows_for_latex(df, include_per_camera=False)
        assert list(default_selection["config_key"]) == ["a_shared"]

        both_selection = _select_cpr_rows_for_latex(df, include_per_camera=True)
        assert set(both_selection["config_key"]) == {"a_shared", "a_percamera"}


class TestSidecarCarriesEnvironment:
    """`test_sidecar_carries_environment` (Task 3 behavior 7)."""

    def test_sidecar_carries_environment(self):
        from aquacal.io import capture_environment
        from experiments.e3_derived_quantities import build_provenance_sidecar

        sidecar = build_provenance_sidecar(42)
        expected_keys = set(capture_environment().keys())
        assert set(sidecar["environment"].keys()) == expected_keys


# --- D-32/CR-05: tier 2 rewired to measure the production (batch) Newton loop ----------


class TestNewtonColumnsIncludeLoop:
    """`NEWTON_COLUMNS`/`NEWTON_KEY_COLUMNS` gain a `loop` column (D-32)."""

    def test_newton_columns_include_loop_and_key_columns_updated(self):
        from experiments.e3_derived_quantities import (
            NEWTON_COLUMNS,
            NEWTON_KEY_COLUMNS,
            NEWTON_LOOP_VALUES,
        )

        assert "loop" in NEWTON_COLUMNS
        assert NEWTON_KEY_COLUMNS == ["camera", "loop"]
        assert set(NEWTON_LOOP_VALUES) == {"scalar", "batch"}


class TestBuildNewtonIterationsDfBothLoops:
    """`build_newton_iterations_df` emits rows for both loops over the same population
    (Task 2 behavior 1), row count doubles to 26 for 12 cameras + ALL (Task 2 behavior 2)."""

    def test_both_loops_represented_with_double_row_count(self):
        from experiments.e3_derived_quantities import (
            NEWTON_COLUMNS,
            NEWTON_LOOP_BATCH,
            NEWTON_LOOP_SCALAR,
            build_newton_iterations_df,
        )

        df = build_newton_iterations_df(n_frames=2, seed=42)

        assert list(df.columns) == NEWTON_COLUMNS
        assert len(df) == 26  # 12 cameras + ALL, times 2 loops
        assert set(df["loop"]) == {NEWTON_LOOP_SCALAR, NEWTON_LOOP_BATCH}
        # Every camera (+ALL) reports exactly one scalar row and one batch row.
        counts = df.groupby("camera")["loop"].nunique()
        assert (counts == 2).all()

    # Frozen literal of the pre-D-32 `newton_iterations.csv` header (D-32/CR-05
    # added the `loop` column to NEWTON_COLUMNS; this is NEWTON_COLUMNS minus
    # `loop`). Anchored here instead of read from the live committed CSV
    # because plan 19.2-23 was written to regenerate that file with the NEW
    # (post-D-32) schema -- the committed copy stopped being "pre-D-32" the
    # moment that regeneration landed and will never be pre-D-32 again. A
    # baseline that lives in a file every plan is entitled to regenerate is
    # not a baseline; freezing it as a literal is the fix that survives the
    # next regeneration too. (An archived pre-D-32 copy under
    # experiments/archive/ was considered and rejected: it would still be an
    # external file another cleanup pass could move or delete without any
    # test failing to notice -- a literal in the test itself cannot drift.)
    _PRE_D32_NEWTON_HEADER = [
        "camera",
        "n_points",
        "iter_min",
        "iter_median",
        "iter_max",
        "n_not_converged",
        "incidence_deg_min",
        "incidence_deg_max",
        "residual_max_m",
    ]

    def test_scalar_rows_unchanged_columns_and_semantics_vs_committed_baseline(self):
        """Scalar rows' column names/semantics match the FROZEN pre-D-32 header
        (see `_PRE_D32_NEWTON_HEADER`'s docstring for why this is a literal and not
        read from the committed CSV), and the loop column uses the fixed vocabulary."""
        from experiments.e3_derived_quantities import (
            NEWTON_LOOP_SCALAR,
            build_newton_iterations_df,
        )

        baseline_header = self._PRE_D32_NEWTON_HEADER

        df = build_newton_iterations_df(n_frames=2, seed=42)
        scalar_df = df[df["loop"] == NEWTON_LOOP_SCALAR]

        # The scalar rows carry every pre-D-32 column (order-independent), plus the new
        # `loop` column as the only addition.
        assert set(baseline_header) <= set(scalar_df.columns)
        assert set(scalar_df.columns) - set(baseline_header) == {"loop"}
        assert set(scalar_df["loop"]) == {NEWTON_LOOP_SCALAR}

    def test_batch_rows_n_not_converged_from_per_point_convergence_flags(self):
        """The batch rows' `n_not_converged` is computed from the batch diagnostic's
        `converged` array, not inferred from a residual threshold (Task 2 behavior 3)."""
        from aquacal.core.refractive_geometry import (
            refractive_project_batch_newton_diagnostic,
        )
        from experiments.e3_derived_quantities import (
            NEWTON_LOOP_BATCH,
            build_newton_iterations_df,
        )

        # Patch the batch diagnostic to force one point to report converged=False,
        # and assert that single non-convergence surfaces in the aggregated row --
        # proving n_not_converged is read from the diagnostic's own flag, not derived
        # from `final_abs_delta` by a threshold comparison in this module.
        def _forced_one_not_converged(camera, interface, points_3d, **kwargs):
            diagnostics = refractive_project_batch_newton_diagnostic(
                camera, interface, points_3d, **kwargs
            )
            if len(diagnostics["converged"]) > 0:
                diagnostics = dict(diagnostics)
                diagnostics["converged"] = diagnostics["converged"].copy()
                diagnostics["converged_at_iteration"] = diagnostics[
                    "converged_at_iteration"
                ].copy()
                diagnostics["converged"][0] = False
                diagnostics["converged_at_iteration"][0] = -1
            return diagnostics

        with patch(
            "experiments.e3_derived_quantities.refractive_project_batch_newton_diagnostic",
            side_effect=_forced_one_not_converged,
        ):
            df = build_newton_iterations_df(n_frames=1, seed=42)

        batch_all_row = df[
            (df["loop"] == NEWTON_LOOP_BATCH) & (df["camera"] == "ALL")
        ].iloc[0]
        assert batch_all_row["n_not_converged"] >= 1


class TestRunCheckHonoursSeed:
    """`_run_check` uses the seed it was given, closing WR-05 (Task 2 behavior 4)."""

    def test_run_check_passes_seed_to_build_newton_iterations_df(self, tmp_path):
        from experiments.e3_derived_quantities import _run_check

        # No committed baselines in tmp_path -> _run_check reports failure for all
        # tiers, but the call under test only cares whether build_newton_iterations_df
        # was invoked with the seed _run_check was given.
        with patch(
            "experiments.e3_derived_quantities.build_newton_iterations_df"
        ) as mock_build:
            mock_build.return_value = pd.DataFrame()
            _run_check(tmp_path, seed=7)

        # newton_path.exists() is False in an empty tmp_path, so build_newton_iterations_df
        # is never called in that branch. Create a stub baseline so the branch executes.
        (tmp_path / "newton_iterations.csv").write_text("camera,loop\n")
        with patch(
            "experiments.e3_derived_quantities.build_newton_iterations_df"
        ) as mock_build:
            mock_build.return_value = pd.DataFrame({"camera": [], "loop": []})
            _run_check(tmp_path, seed=7)

        mock_build.assert_called_once_with(n_frames=100, seed=7)


class TestStructuralScalingDf:
    """COV-01 Task 2: `build_structural_scaling_df` -- the widened structural sweep, its own
    separate artifact, never touching `cpr_grouping.csv`/`.tex` (T-19.5-01-02).
    """

    def test_structural_scaling_columns_match_declared_schema(self):
        from experiments.e3_derived_quantities import (
            SCALING_COLUMNS,
            build_structural_scaling_df,
        )

        df = build_structural_scaling_df()
        assert list(df.columns) == SCALING_COLUMNS
        assert len(SCALING_COLUMNS) == 13

    def test_structural_scaling_row_count_matches_configs(self):
        from experiments.e3_derived_quantities import (
            SCALING_CONFIGS,
            build_structural_scaling_df,
        )

        df = build_structural_scaling_df()
        assert len(df) == len(SCALING_CONFIGS)

    def test_computed_rows_pin_group_count_at_13_or_17(self):
        """The pinning claim COV-01 must substantiate: n_groups is invariant to n_cameras
        and n_frames across the whole computed range, 13 without intrinsics / 17 with."""
        from experiments.e3_derived_quantities import build_structural_scaling_df

        df = build_structural_scaling_df()
        computed = df[df["record_source"] == "computed"]
        assert len(computed) > 0

        not_intrinsics = computed[~computed["refine_intrinsics"]]
        assert len(not_intrinsics) > 0
        assert (not_intrinsics["n_groups"] == 13).all()

        with_intrinsics = computed[computed["refine_intrinsics"]]
        assert len(with_intrinsics) > 0
        assert (with_intrinsics["n_groups"] == 17).all()

    def test_sweep_straddles_the_dense_sparse_boundary(self):
        from experiments.e3_derived_quantities import build_structural_scaling_df

        df = build_structural_scaling_df()
        assert (df["exceeds_dense_threshold"]).any()
        assert (~df["exceeds_dense_threshold"]).any()

    def test_exceeds_dense_threshold_consistent_with_jacobian_elements(self):
        from experiments.e3_derived_quantities import (
            _DENSE_THRESHOLD_ELEMENTS,
            build_structural_scaling_df,
        )

        df = build_structural_scaling_df()
        expected = df["jacobian_elements"] > _DENSE_THRESHOLD_ELEMENTS
        assert (df["exceeds_dense_threshold"] == expected).all()

    def test_predicted_rows_never_allocate_and_have_null_derived_fields(self):
        from experiments.e3_derived_quantities import build_structural_scaling_df

        df = build_structural_scaling_df()
        predicted = df[df["record_source"] == "predicted"]
        assert len(predicted) > 0
        assert predicted["n_groups"].isna().all()
        assert predicted["nnz"].isna().all()
        assert predicted["fd_reduction"].isna().all()

    def test_never_touches_cpr_grouping_csv_or_tex(self, tmp_path):
        """`build_structural_scaling_df` takes no path argument and reads no file --
        the separate-tier guarantee (design_decision, T-19.5-01-02) is structural, not just
        behavioral: there is no `cpr_grouping` write call or E2-benchmark read in its call
        graph to touch."""
        import inspect

        from experiments.e3_derived_quantities import build_structural_scaling_df

        source = inspect.getsource(build_structural_scaling_df)
        assert "write_cpr_latex" not in source
        assert "_build_copied_cpr_row" not in source
        assert "_E2_BENCHMARK_JSON_PATH" not in source
        assert "write_experiment_csv" not in source
