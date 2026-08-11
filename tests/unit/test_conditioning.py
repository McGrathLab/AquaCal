"""Unit tests for conditioning diagnostics (accuracy, memory, chunking, IO)."""

from __future__ import annotations

import tracemalloc

import numpy as np
import pytest
import scipy.linalg
import scipy.sparse

from aquacal.validation.conditioning import (
    ConditioningMemoryError,
    compute_conditioning,
    load_conditioning_report,
    save_conditioning_report,
)


def _near_degenerate_jacobian(m=5000, n=40, seed=0):
    rng = np.random.default_rng(seed)
    J = rng.standard_normal((m, n))
    J[:, 1] = J[:, 0] + 1e-9 * rng.standard_normal(m)
    return J


def test_sigma_min_matches_reference_on_near_degenerate_jacobian():
    J = _near_degenerate_jacobian()
    report = compute_conditioning(J)
    s_ref = scipy.linalg.svd(J, compute_uv=False)

    assert abs(report.singular_values[-1] - s_ref[-1]) / s_ref[-1] < 1e-6
    cond_ref = s_ref[0] / s_ref[-1]
    assert abs(report.condition_number - cond_ref) / cond_ref < 1e-6


def test_correlation_flags_degenerate_pair():
    J = _near_degenerate_jacobian()
    report = compute_conditioning(J)

    assert abs(report.correlation[0, 1]) > 0.99
    assert np.allclose(np.diag(report.correlation), 1.0)
    assert np.all(np.abs(report.correlation) <= 1.0 + 1e-9)


def test_correlation_near_identity_for_orthogonal_columns():
    rng = np.random.default_rng(1)
    m, n = 500, 20
    tall = rng.standard_normal((m, n))
    Q, _ = np.linalg.qr(tall)
    J = Q  # orthonormal columns

    report = compute_conditioning(J)
    off_diag = report.correlation - np.diag(np.diag(report.correlation))
    assert np.all(np.abs(off_diag) < 0.05)


def test_chunk_size_invariance():
    J = _near_degenerate_jacobian()
    report_small = compute_conditioning(J, chunk_rows=64)
    report_large = compute_conditioning(J, chunk_rows=10_000)

    # rtol=1e-9 for the well-conditioned bulk of the spectrum; the smallest
    # singular value lives in the near-degenerate direction this test injects,
    # so its own floating-point noise floor is ~1e-7 (matches the ~7.2e-8
    # blocked-TSQR accuracy measured in 16-RESEARCH.md's Addendum) regardless
    # of chunking -- compare it separately at that looser tolerance.
    np.testing.assert_allclose(
        report_small.singular_values[:-1], report_large.singular_values[:-1], rtol=1e-9
    )
    np.testing.assert_allclose(
        report_small.singular_values[-1], report_large.singular_values[-1], rtol=1e-6
    )


def test_peak_memory_independent_of_rows():
    m, n = 200_000, 50
    rng = np.random.default_rng(2)
    J = rng.standard_normal((m, n))

    tracemalloc.start()
    tracemalloc.clear_traces()
    _, peak_before = tracemalloc.get_traced_memory()
    compute_conditioning(J, chunk_rows=8192)
    _, peak_after = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_extra_mb = (peak_after - peak_before) / 1e6
    assert peak_extra_mb < 60, f"peak extra memory {peak_extra_mb:.1f} MB exceeds 60 MB"


def test_underdetermined_raises():
    rng = np.random.default_rng(3)
    J = rng.standard_normal((10, 40))
    with pytest.raises(ValueError):
        compute_conditioning(J)


def test_memory_precheck_refuses_loudly():
    rng = np.random.default_rng(4)
    J = rng.standard_normal((5000, 40))
    with pytest.raises(ConditioningMemoryError) as exc_info:
        compute_conditioning(J, max_bytes=1000)
    assert "save_conditioning" in str(exc_info.value)


def test_accepts_sparse_jacobian():
    rng = np.random.default_rng(5)
    J_dense = rng.standard_normal((2000, 30))
    J_sparse = scipy.sparse.csr_matrix(J_dense)

    report_dense = compute_conditioning(J_dense)
    report_sparse = compute_conditioning(J_sparse)

    np.testing.assert_allclose(
        report_dense.singular_values, report_sparse.singular_values, rtol=1e-9
    )


def test_save_and_load_roundtrip(tmp_path):
    J = _near_degenerate_jacobian(m=1000, n=20)
    report = compute_conditioning(J)
    json_path = tmp_path / "conditioning.json"
    npz_path = tmp_path / "conditioning.npz"

    save_conditioning_report(report, json_path, npz_path)
    loaded = load_conditioning_report(json_path, npz_path)

    np.testing.assert_array_equal(loaded.correlation, report.correlation)
    assert loaded.rank == report.rank
    assert loaded.n_params == report.n_params
    assert loaded.n_residuals == report.n_residuals
    assert loaded.rank_tolerance == report.rank_tolerance
    assert abs(loaded.condition_number - report.condition_number) < 1e-9


def test_json_contains_spectrum_not_matrix(tmp_path):
    import json

    J = _near_degenerate_jacobian(m=1000, n=20)
    report = compute_conditioning(J)
    json_path = tmp_path / "conditioning.json"
    npz_path = tmp_path / "conditioning.npz"

    save_conditioning_report(report, json_path, npz_path)

    with open(json_path) as f:
        payload = json.load(f)

    assert "singular_values" in payload
    assert "correlation" not in payload


def test_overwrite_warns(tmp_path, caplog):
    J = _near_degenerate_jacobian(m=1000, n=20)
    report = compute_conditioning(J)
    json_path = tmp_path / "conditioning.json"
    npz_path = tmp_path / "conditioning.npz"

    save_conditioning_report(report, json_path, npz_path)
    with caplog.at_level("WARNING"):
        save_conditioning_report(report, json_path, npz_path)

    assert any(str(json_path) in record.message for record in caplog.records)


def test_conditioning_is_importable_but_not_advertised():
    # Narrowing `aquacal.validation.__all__` was deliberate and pre-2.0.0: the
    # conditioning API's own docstrings call it experimental ("return shape may
    # change") and `docs/api/validation.rst` never documented it, so it was never
    # a supported surface. The names stay importable -- only the advertised
    # surface narrows.
    import aquacal.validation as validation_module
    from aquacal.validation import ConditioningReport
    from aquacal.validation import compute_conditioning as public_compute_conditioning

    assert public_compute_conditioning is compute_conditioning
    assert ConditioningReport is not None
    assert "compute_conditioning" not in validation_module.__all__
    assert "ConditioningReport" not in validation_module.__all__
    assert "save_conditioning_report" not in validation_module.__all__
