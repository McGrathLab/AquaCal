"""Conditioning and parameter-correlation diagnostics at the optimizer solution."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy.linalg
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class ConditioningMemoryError(MemoryError):
    """Raised when conditioning diagnostics would exceed the allowed allocation."""


@dataclass
class ConditioningReport:
    """Singular-value spectrum and parameter correlation at the optimizer solution.

    Attributes:
        singular_values: Singular values of the solution-point Jacobian, shape (n,),
            descending order.
        condition_number: Ratio ``singular_values[0] / singular_values[-1]``.
            ``math.inf`` when the smallest singular value is exactly zero.
        correlation: Parameter correlation matrix, shape (n, n), unit diagonal,
            values clipped to [-1, 1].
        rank: Number of singular values retained above ``rank_tolerance``.
        rank_tolerance: Absolute threshold used to truncate near-zero singular
            values before forming the correlation matrix.
        n_params: Number of columns (parameters), ``n``.
        n_residuals: Number of rows (residuals), ``m``.
        parameter_names: Optional per-parameter names, length ``n`` when provided.
    """

    singular_values: NDArray[np.float64]
    condition_number: float
    correlation: NDArray[np.float64]
    rank: int
    rank_tolerance: float
    n_params: int
    n_residuals: int
    parameter_names: list[str] | None = None


def compute_conditioning(
    jac,
    parameter_names: list[str] | None = None,
    chunk_rows: int = 8192,
    rank_rtol: float = 1e-12,
    max_bytes: int = 2_000_000_000,
) -> ConditioningReport:
    """Compute the singular-value spectrum and parameter correlation of a Jacobian.

    Uses a blocked tall-skinny QR reduction followed by a single SVD of the
    resulting (n, n) R factor, so peak extra memory is O(chunk_rows * n_params)
    rather than scaling with the number of residuals.

    Note: Experimental -- return shape may change before it is exercised by the
    WP6 analysis.

    Args:
        jac: Jacobian at the solution, shape (m, n). May be a dense ndarray or
            any object exposing ``.toarray()`` (e.g. a scipy sparse matrix).
        parameter_names: Optional per-parameter names, length must equal ``n``.
        chunk_rows: Number of rows processed per blocked-QR step.
        rank_rtol: Relative tolerance (against the largest singular value) used
            to determine numerical rank before forming the correlation matrix.
        max_bytes: Maximum estimated extra memory (bytes) the algorithm is
            allowed to use. Raises :class:`ConditioningMemoryError` if the
            analytic estimate exceeds this.

    Returns:
        Populated :class:`ConditioningReport`.

    Raises:
        ValueError: If ``m < n`` (underdetermined system), if
            ``parameter_names`` has the wrong length, or if the Jacobian is
            degenerate (rank 0).
        ConditioningMemoryError: If the analytic memory estimate exceeds
            ``max_bytes``.
        RuntimeError: If the blocked QR reduction does not yield an (n, n)
            R factor (internal invariant violation).
    """
    m, n = jac.shape
    if m < n:
        raise ValueError(
            f"Jacobian is underdetermined (m={m} residuals < n={n} parameters); "
            "conditioning at the solution is undefined."
        )
    if parameter_names is not None and len(parameter_names) != n:
        raise ValueError(
            f"parameter_names has length {len(parameter_names)} but jac has "
            f"n={n} columns."
        )

    # Analytic memory pre-check. The algorithm's transient is O(chunk * n),
    # independent of m, so a cheap closed form is sufficient -- no psutil probing.
    block = max(chunk_rows, n)
    est = (block + n) * n * 8 * 3  # stacked copy + LAPACK workspace + R
    est += n * n * 8 * 4  # V, cov, corr, scratch
    if est > max_bytes:
        est_gb = est / 1e9
        raise ConditioningMemoryError(
            f"Estimated conditioning memory ({est_gb:.2f} GB) exceeds max_bytes "
            f"({max_bytes / 1e9:.2f} GB) for m={m}, n={n}. Set "
            "'save_conditioning: false' in the config to skip this diagnostic."
        )

    # Blocked tall-skinny QR reduction. Never hold a reference to the full
    # jac beyond this loop -- that is the point of chunking.
    R = np.zeros((0, n), dtype=np.float64)
    for start in range(0, m, block):
        chunk = jac[start : start + block]
        if hasattr(chunk, "toarray"):
            chunk = chunk.toarray()
        else:
            chunk = np.asarray(chunk, dtype=np.float64)
        # The "economic" qr mode is mandatory here: the default R-only mode
        # returns an (m, n) factor rather than (n, n), which would feed an
        # m-row matrix into the SVD below and allocate an m x m U (the OOM
        # trap that crashed a machine during planning -- see the oom_trap
        # note in 16-01-PLAN.md).
        R = scipy.linalg.qr(np.vstack([R, chunk]), mode="economic")[1]

    if R.shape != (n, n):
        raise RuntimeError(
            f"Blocked QR reduction produced R with shape {R.shape}, expected "
            f"({n}, {n}). This indicates the economic qr mode was not "
            "honored somewhere in the reduction (see the OOM trap noted "
            "above)."
        )

    # Single SVD of the small (n, n) R factor. full_matrices=False is mandatory:
    # the default (True) would allocate an (n, n) U here, which is fine at this
    # size, but the pattern must never be copy-pasted onto the full (m, n) jac.
    _, s, Vt = scipy.linalg.svd(R, full_matrices=False)
    V = Vt.T

    # QR can flip signs into R; singular values must be non-negative.
    s = np.abs(s)
    order = np.argsort(s)[::-1]
    s = s[order]
    V = V[:, order]

    if s[-1] == 0.0:
        condition_number = math.inf
    else:
        condition_number = float(s[0] / s[-1])

    tol = rank_rtol * s[0]
    keep = s > tol
    rank = int(keep.sum())
    if rank == 0:
        raise ValueError(
            "Jacobian is degenerate (rank 0 at the given rank_rtol); nothing to report."
        )

    Vk = V[:, keep]
    cov = (Vk / s[keep] ** 2) @ Vk.T
    d = np.sqrt(np.diag(cov))
    corr = cov / np.outer(d, d)
    np.fill_diagonal(corr, 1.0)
    corr = np.clip(corr, -1.0, 1.0)

    return ConditioningReport(
        singular_values=s,
        condition_number=condition_number,
        correlation=corr,
        rank=rank,
        rank_tolerance=float(tol),
        n_params=n,
        n_residuals=m,
        parameter_names=parameter_names,
    )


def save_conditioning_report(
    report: ConditioningReport,
    json_path: Path,
    npz_path: Path,
    stage: str | None = None,
) -> None:
    """Write a conditioning report to disk as a JSON scalars/spectrum file plus NPZ.

    Scalars and the singular-value spectrum go to JSON (human-readable,
    greppable, quotable in the paper); the (n, n) correlation matrix goes to
    NPZ (compact, exact float round-trip). The matrix is never serialized as
    JSON.

    Note: Experimental -- return shape may change before it is exercised by the
    WP6 analysis.

    Args:
        report: Report produced by :func:`compute_conditioning`.
        json_path: Destination for the JSON scalars/spectrum payload.
        npz_path: Destination for the NPZ correlation-matrix payload.
        stage: Optional label naming the bundle-adjustment stage that produced
            this report (e.g. "stage3", "stage3_intrinsic_pass"), recorded in
            the JSON payload as ``"stage"`` for unambiguous provenance when a
            run only reports one conditioning pass.

    Raises:
        None directly; overwriting an existing path only logs a warning.
    """
    json_path = Path(json_path)
    npz_path = Path(npz_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    npz_path.parent.mkdir(parents=True, exist_ok=True)

    if json_path.exists():
        logger.warning("Overwriting existing conditioning JSON at %s", json_path)
    if npz_path.exists():
        logger.warning("Overwriting existing conditioning NPZ at %s", npz_path)

    payload = {
        # None when not finite -- condition_number == inf is not JSON-safe.
        "condition_number": (
            report.condition_number if math.isfinite(report.condition_number) else None
        ),
        "singular_values": report.singular_values.tolist(),
        "rank": report.rank,
        "rank_tolerance": report.rank_tolerance,
        "n_params": report.n_params,
        "n_residuals": report.n_residuals,
        "parameter_names": report.parameter_names,
        "correlation_npz": npz_path.name,
        "stage": stage,
    }
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2)

    npz_kwargs = {
        "correlation": report.correlation,
        "singular_values": report.singular_values,
    }
    if report.parameter_names is not None:
        npz_kwargs["parameter_names"] = np.array(report.parameter_names)
    np.savez_compressed(npz_path, **npz_kwargs)


def load_conditioning_report(json_path: Path, npz_path: Path) -> ConditioningReport:
    """Load a conditioning report previously written by :func:`save_conditioning_report`.

    Note: Experimental -- return shape may change before it is exercised by the
    WP6 analysis.

    Args:
        json_path: Path to the JSON scalars/spectrum payload.
        npz_path: Path to the NPZ correlation-matrix payload.

    Returns:
        Reconstructed :class:`ConditioningReport`.
    """
    with open(json_path) as f:
        payload = json.load(f)

    npz = np.load(npz_path, allow_pickle=False)
    correlation = npz["correlation"]
    singular_values = npz["singular_values"]

    condition_number = payload["condition_number"]
    if condition_number is None:
        condition_number = math.inf

    return ConditioningReport(
        singular_values=singular_values,
        condition_number=float(condition_number),
        correlation=correlation,
        rank=payload["rank"],
        rank_tolerance=payload["rank_tolerance"],
        n_params=payload["n_params"],
        n_residuals=payload["n_residuals"],
        parameter_names=payload["parameter_names"],
    )
