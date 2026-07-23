"""Tests for OptimizerObserver: scipy least_squares callback/fun/jac wrapping."""

import csv
import math

import numpy as np
import pytest
from scipy.optimize import least_squares

from aquacal.calibration._observability import (
    TRACE_CSV_HEADER,
    OptimizerObserver,
    TraceRow,
    build_parameter_labels,
)
from aquacal.calibration._optim_common import pack_params
from aquacal.config.schema import BoardPose, CameraExtrinsics, CameraIntrinsics
from aquacal.validation.conditioning import ConditioningMemoryError, ConditioningReport

# --- A tiny, real (non-mocked) least_squares problem: two independent
# Rosenbrock-style 2-parameter blocks stacked to n=4 params, m=4 residuals.
# x0 is deliberately far from the (1, 1, 1, 1) minimum so several iterations
# are needed, giving the tests real per-iteration data to inspect.
X0 = np.array([-1.2, 1.0, -1.2, 1.0], dtype=np.float64)


def rosenbrock_residuals(x: np.ndarray) -> np.ndarray:
    return np.array(
        [
            10.0 * (x[1] - x[0] ** 2),
            1.0 - x[0],
            10.0 * (x[3] - x[2] ** 2),
            1.0 - x[2],
        ],
        dtype=np.float64,
    )


def rosenbrock_jac(x: np.ndarray) -> np.ndarray:
    J = np.zeros((4, 4), dtype=np.float64)
    J[0, 0] = -20.0 * x[0]
    J[0, 1] = 10.0
    J[1, 0] = -1.0
    J[2, 2] = -20.0 * x[2]
    J[2, 3] = 10.0
    J[3, 2] = -1.0
    return J


def _run_observed(stage: str = "test_stage"):
    """Run the Rosenbrock problem through least_squares with an observer attached."""
    observer = OptimizerObserver(stage=stage, water_z_index=2, normal_fixed=False)
    fun = observer.wrap_fun(rosenbrock_residuals)
    jac = observer.wrap_jac(rosenbrock_jac)
    result = least_squares(
        fun,
        x0=X0,
        jac=jac,
        method="trf",
        callback=observer.callback,
    )
    return observer, result


class TestRowCapture:
    def test_rows_captured_per_accepted_iteration(self):
        observer, result = _run_observed()
        assert len(observer.rows) >= 2
        iterations = [row.iteration for row in observer.rows]
        assert iterations == sorted(iterations)
        assert all(b > a for a, b in zip(iterations, iterations[1:]))

    def test_cost_is_monotonically_non_increasing(self):
        observer, result = _run_observed()
        costs = [row.cost for row in observer.rows]
        assert all(b <= a for a, b in zip(costs, costs[1:]))

    def test_step_norm_matches_manual_difference(self):
        observer = OptimizerObserver(stage="test_stage")
        fun = observer.wrap_fun(rosenbrock_residuals)
        jac = observer.wrap_jac(rosenbrock_jac)

        xs: list[np.ndarray] = []

        def combined_callback(intermediate_result):
            xs.append(np.array(intermediate_result.x, copy=True))
            observer.callback(intermediate_result)

        least_squares(
            fun,
            x0=X0,
            jac=jac,
            method="trf",
            callback=combined_callback,
        )

        assert len(xs) == len(observer.rows)
        assert observer.rows[0].step_norm == 0.0
        for i in range(1, len(xs)):
            expected = float(np.linalg.norm(xs[i] - xs[i - 1]))
            assert observer.rows[i].step_norm == expected

    def test_optimality_proxy_matches_direct_computation(self):
        observer, result = _run_observed()
        last_row = observer.rows[-1]

        J_final = rosenbrock_jac(result.x)
        f_final = rosenbrock_residuals(result.x)
        expected_optimality = float(np.linalg.norm(J_final.T @ f_final, np.inf))

        np.testing.assert_allclose(last_row.optimality, expected_optimality, rtol=1e-12)

    def test_optimality_nan_when_jac_is_string(self):
        observer = OptimizerObserver(stage="test_stage")
        fun = observer.wrap_fun(rosenbrock_residuals)
        jac = observer.wrap_jac("2-point")

        assert jac == "2-point"

        least_squares(
            fun,
            x0=X0,
            jac=jac,
            method="trf",
            callback=observer.callback,
        )

        assert len(observer.rows) >= 1
        assert all(math.isnan(row.optimality) for row in observer.rows)


class TestZeroNumericalChange:
    def test_wrappers_do_not_change_the_solution(self):
        """The most important test in this file: observed vs. unobserved solves
        must produce bit-identical results."""
        result_unwrapped = least_squares(
            rosenbrock_residuals,
            x0=X0,
            jac=rosenbrock_jac,
            method="trf",
        )

        observer = OptimizerObserver(stage="test_stage")
        fun = observer.wrap_fun(rosenbrock_residuals)
        jac = observer.wrap_jac(rosenbrock_jac)
        result_wrapped = least_squares(
            fun,
            x0=X0,
            jac=jac,
            method="trf",
            callback=observer.callback,
        )

        np.testing.assert_array_equal(result_wrapped.x, result_unwrapped.x)
        assert result_wrapped.cost == result_unwrapped.cost


class TestMemorySafety:
    def test_observer_holds_no_jacobian_reference(self):
        observer, _ = _run_observed()
        for value in vars(observer).values():
            if isinstance(value, np.ndarray):
                assert value.ndim != 2, (
                    "Observer must never retain a 2D (Jacobian-shaped) array"
                )


class TestWriteTraceCsv:
    def test_write_trace_csv_shape(self, tmp_path):
        observer, _ = _run_observed()
        path = tmp_path / "trace_test.csv"
        observer.write_trace_csv(path)

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == TRACE_CSV_HEADER
            rows = list(reader)

        assert len(rows) == len(observer.rows)

    def test_write_trace_csv_warns_on_overwrite(self, tmp_path, caplog):
        observer, _ = _run_observed()
        path = tmp_path / "trace_test.csv"
        observer.write_trace_csv(path)

        with caplog.at_level("WARNING"):
            observer.write_trace_csv(path)

        assert any("Overwriting" in rec.message for rec in caplog.records)


class TestTraceRowDataclass:
    def test_trace_row_fields(self):
        row = TraceRow(
            iteration=0,
            n_fev=1,
            cost=1.0,
            step_norm=0.0,
            optimality=float("nan"),
            water_z=0.15,
            tilt_rx=float("nan"),
            tilt_ry=float("nan"),
        )
        assert row.iteration == 0
        assert row.water_z == 0.15


# --- build_parameter_labels ---------------------------------------------------

CAMERA_ORDER = ["camA", "camB", "camC"]
FRAME_ORDER = [10, 20]
REFERENCE_CAMERA = "camA"


def _pack_params_fixture(
    refine_intrinsics: bool, normal_fixed: bool, shared_interface: bool = True
) -> np.ndarray:
    """Build a small pack_params(...) vector matching CAMERA_ORDER/FRAME_ORDER."""
    extrinsics = {
        cam: CameraExtrinsics(R=np.eye(3), t=np.array([1.0, 2.0, 3.0]))
        for cam in CAMERA_ORDER
    }
    board_poses = {
        frame_idx: BoardPose(
            frame_idx=frame_idx,
            rvec=np.array([0.1, 0.2, 0.3]),
            tvec=np.array([0.4, 0.5, 0.6]),
        )
        for frame_idx in FRAME_ORDER
    }
    intrinsics = None
    if refine_intrinsics:
        intrinsics = {
            cam: CameraIntrinsics(
                K=np.array([[100.0, 0, 50.0], [0, 100.0, 50.0], [0, 0, 1]]),
                dist_coeffs=np.zeros(5),
                image_size=(100, 100),
            )
            for cam in CAMERA_ORDER
        }
    return pack_params(
        extrinsics=extrinsics,
        water_z=0.15,
        board_poses=board_poses,
        reference_camera=REFERENCE_CAMERA,
        camera_order=CAMERA_ORDER,
        frame_order=FRAME_ORDER,
        intrinsics=intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
    )


class TestBuildParameterLabels:
    @pytest.mark.parametrize("refine_intrinsics", [False, True])
    @pytest.mark.parametrize("normal_fixed", [False, True])
    def test_parameter_labels_length_matches_packed_vector(
        self, refine_intrinsics, normal_fixed
    ):
        x0 = _pack_params_fixture(refine_intrinsics, normal_fixed)
        labels = build_parameter_labels(
            CAMERA_ORDER,
            FRAME_ORDER,
            REFERENCE_CAMERA,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )
        assert len(labels) == len(x0)

    @pytest.mark.parametrize("normal_fixed", [False, True])
    def test_parameter_labels_water_z_index(self, normal_fixed):
        labels = build_parameter_labels(
            CAMERA_ORDER,
            FRAME_ORDER,
            REFERENCE_CAMERA,
            refine_intrinsics=False,
            normal_fixed=normal_fixed,
        )
        expected_index = (0 if normal_fixed else 2) + 6 * (len(CAMERA_ORDER) - 1)
        assert labels.index("water_z") == expected_index

    def test_reference_camera_has_no_extrinsic_labels(self):
        labels = build_parameter_labels(
            CAMERA_ORDER,
            FRAME_ORDER,
            REFERENCE_CAMERA,
            refine_intrinsics=False,
            normal_fixed=True,
        )
        assert not any(
            label.startswith(f"{REFERENCE_CAMERA}_rvec")
            or label.startswith(f"{REFERENCE_CAMERA}_tvec")
            for label in labels
        )

    @pytest.mark.parametrize("refine_intrinsics", [False, True])
    @pytest.mark.parametrize("normal_fixed", [False, True])
    def test_per_camera_labels_length_matches_packed_vector(
        self, refine_intrinsics, normal_fixed
    ):
        """shared_interface=False labels align 1:1 with the per-camera packed vector."""
        x0 = _pack_params_fixture(
            refine_intrinsics, normal_fixed, shared_interface=False
        )
        labels = build_parameter_labels(
            CAMERA_ORDER,
            FRAME_ORDER,
            REFERENCE_CAMERA,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=False,
        )
        assert len(labels) == len(x0)

    def test_per_camera_water_z_labels_one_per_camera_in_order(self):
        """shared_interface=False emits one {cam}_water_z label per camera, in order."""
        labels = build_parameter_labels(
            CAMERA_ORDER,
            FRAME_ORDER,
            REFERENCE_CAMERA,
            shared_interface=False,
        )
        water_z_labels = [label for label in labels if label.endswith("_water_z")]
        assert water_z_labels == [f"{cam}_water_z" for cam in CAMERA_ORDER]
        assert "water_z" not in labels


# --- OptimizerObserver.on_solution / conditioning ------------------------------


def _run_observed_conditioning(conditioning: bool = True):
    """Run the Rosenbrock problem with conditioning enabled, calling on_solution."""
    observer = OptimizerObserver(stage="test_stage", conditioning=conditioning)
    observer.configure_layout(
        water_z_index=2,
        normal_fixed=False,
        parameter_labels=["p0", "p1", "p2", "p3"],
    )
    fun = observer.wrap_fun(rosenbrock_residuals)
    jac = observer.wrap_jac(rosenbrock_jac)
    result = least_squares(
        fun,
        x0=X0,
        jac=jac,
        method="trf",
        callback=observer.callback,
    )
    observer.on_solution(result)
    return observer, result


class TestOnSolutionConditioning:
    def test_on_solution_populates_report_when_enabled(self):
        observer, result = _run_observed_conditioning(conditioning=True)
        assert isinstance(observer.conditioning_report, ConditioningReport)
        assert observer.conditioning_report.n_params == len(result.x)

    def test_on_solution_noop_when_disabled(self):
        observer, _ = _run_observed_conditioning(conditioning=False)
        assert observer.conditioning_report is None

    def test_observer_does_not_retain_jacobian_after_conditioning(self):
        observer, _ = _run_observed_conditioning(conditioning=True)
        n_params = observer.conditioning_report.n_params
        for value in vars(observer).values():
            if isinstance(value, np.ndarray) and value.ndim == 2:
                assert value.shape[0] <= n_params, (
                    "Observer must never retain a Jacobian-shaped (m, n) array; "
                    "only the small (n, n) correlation matrix inside the report "
                    "is permitted."
                )

    def test_memory_error_propagates_with_stage_name(self, monkeypatch):
        observer = OptimizerObserver(stage="stage3", conditioning=True)
        observer.configure_layout(water_z_index=2, normal_fixed=False)

        def _raise_memory_error(*args, **kwargs):
            raise ConditioningMemoryError("boom")

        monkeypatch.setattr(
            "aquacal.validation.conditioning.compute_conditioning",
            _raise_memory_error,
        )

        class _FakeResult:
            jac = np.zeros((4, 4))

        with pytest.raises(ConditioningMemoryError) as excinfo:
            observer.on_solution(_FakeResult())

        assert "stage3" in str(excinfo.value)
        assert "boom" in str(excinfo.value)
