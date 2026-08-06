"""Unit tests for `experiments.fd_jacobian_accuracy`'s pure analysis functions (COV-02).

All tests construct Jacobian pairs by hand (small numpy arrays); none calls a
calibration, imports `least_squares`, or reads a file under
`experiments/results/`.
"""

from __future__ import annotations

import numpy as np
import pytest

from experiments.fd_jacobian_accuracy import (
    build_arg_parser,
    compare_jacobians,
    induced_step_change,
    newton_floor_probe,
    richardson_reference,
)


class TestCompareJacobians:
    def test_identical_matrices_have_zero_max_error(self):
        j = np.array([[1.0, 2.0], [3.0, 4.0]])
        result = compare_jacobians(j, j.copy())
        assert result["max_rel_error"] == 0.0
        assert result["median_rel_error"] == 0.0

    def test_perturbed_column_drives_argmax(self):
        j_reference = np.array([[1.0, 0.0, 5.0], [2.0, 0.0, 5.0], [3.0, 0.0, 5.0]])
        j_test = j_reference.copy()
        # Column 2 gets a large perturbation; columns 0 stays exact.
        j_test[:, 2] = j_reference[:, 2] + 10.0

        result = compare_jacobians(j_test, j_reference)
        assert result["argmax_column"] == 2
        assert result["max_rel_error"] > 0.0

    def test_zero_norm_reference_column_produces_no_inf_or_nan(self):
        j_reference = np.array([[1.0, 0.0], [2.0, 0.0]])
        j_test = np.array([[1.0, 3.0], [2.0, 4.0]])  # column 1 nonzero in test

        result = compare_jacobians(j_test, j_reference)
        for key in ("max_rel_error", "median_rel_error"):
            assert np.isfinite(result[key])
        assert result["n_columns_skipped"] == 1
        assert result["n_columns"] == 2

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError):
            compare_jacobians(np.zeros((2, 2)), np.zeros((2, 3)))

    def test_all_columns_zero_norm_reference_returns_zero_without_crashing(self):
        j_reference = np.zeros((3, 2))
        j_test = np.ones((3, 2))
        result = compare_jacobians(j_test, j_reference)
        assert result["max_rel_error"] == 0.0
        assert result["argmax_column"] is None
        assert result["n_columns_skipped"] == 2


class TestRichardsonReference:
    def test_recovers_exact_derivative_for_quadratic(self):
        # f(x) = x^2, f'(x) = 2x. A 2-point forward difference at step h has
        # error f''(x)/2 * h + O(h^2) = h (since f''(x)=2 here), which is
        # exactly cancelled by the two-step Richardson combination
        # 2*J(h/2) - J(h) for this quadratic (no higher-order terms exist).
        x = 3.0
        true_derivative = 2 * x

        def forward_diff(h: float) -> float:
            return ((x + h) ** 2 - x**2) / h

        h = 0.1
        j_at_h = np.array([[forward_diff(h)]])
        j_at_half_h = np.array([[forward_diff(h / 2)]])

        reference = richardson_reference(j_at_h, j_at_half_h)
        assert reference[0, 0] == pytest.approx(true_derivative, abs=1e-9)

    def test_shape_preserved(self):
        j_at_h = np.ones((4, 3))
        j_at_half_h = np.ones((4, 3)) * 2
        result = richardson_reference(j_at_h, j_at_half_h)
        assert result.shape == (4, 3)


class TestInducedStepChange:
    def test_identical_jacobians_produce_zero_change(self):
        j = np.array([[1.0, 0.0], [0.0, 1.0]])
        residual = np.array([1.0, 2.0])
        assert induced_step_change(j, j.copy(), residual) == pytest.approx(0.0)

    def test_different_jacobians_produce_nonzero_change(self):
        j_test = np.array([[1.0, 0.0], [0.0, 1.0]])
        j_reference = np.array([[2.0, 0.0], [0.0, 2.0]])
        residual = np.array([1.0, 2.0])
        result = induced_step_change(j_test, j_reference, residual)
        assert result > 0.0

    def test_zero_reference_step_and_zero_test_step_is_zero(self):
        j = np.zeros((2, 2))
        residual = np.zeros(2)
        assert induced_step_change(j, j.copy(), residual) == 0.0

    def test_uses_least_squares_not_explicit_inverse(self):
        # Overdetermined system (more residuals than params): a normal-
        # equations inverse would need J.T @ J; np.linalg.lstsq handles the
        # rectangular case directly. This just asserts it does not crash and
        # returns a finite value on a rectangular Jacobian.
        j = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        residual = np.array([1.0, 2.0, 3.0])
        result = induced_step_change(j, j.copy(), residual)
        assert np.isfinite(result)


class TestNewtonFloorProbe:
    def test_decreasing_then_flattening_curve_detects_plateau(self):
        rel_steps = [1e-4, 1e-5, 1e-6, 1e-7, 1e-8]
        errors = [1e-2, 1e-4, 1e-6, 1e-6, 1e-6]
        result = newton_floor_probe(rel_steps, errors)
        assert result["plateau_detected"] is True

    def test_monotonically_decreasing_curve_no_plateau(self):
        rel_steps = [1e-4, 1e-5, 1e-6, 1e-7, 1e-8]
        errors = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5]
        result = newton_floor_probe(rel_steps, errors)
        assert result["plateau_detected"] is False
        assert result["first_non_monotonic_step"] is None

    def test_non_monotonic_tail_reports_first_offending_step(self):
        rel_steps = [1e-4, 1e-5, 1e-6, 1e-7, 1e-8]
        errors = [1e-1, 1e-3, 1e-5, 1e-4, 1e-3]  # goes back up at index 3
        result = newton_floor_probe(rel_steps, errors)
        assert result["plateau_detected"] is True
        assert result["first_non_monotonic_step"] == 1e-7

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            newton_floor_probe([1e-4, 1e-5], [1e-2])

    def test_single_point_curve_is_not_a_plateau(self):
        result = newton_floor_probe([1e-4], [1e-2])
        assert result["plateau_detected"] is False


class TestCliContract:
    def test_shared_five_flag_contract_present(self):
        parser = build_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke", "-h"]
