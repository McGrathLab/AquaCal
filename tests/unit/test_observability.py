"""Tests for OptimizerObserver: scipy least_squares callback/fun/jac wrapping."""

import csv
import math

import numpy as np
from scipy.optimize import least_squares

from aquacal.calibration._observability import (
    TRACE_CSV_HEADER,
    OptimizerObserver,
    TraceRow,
)

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
