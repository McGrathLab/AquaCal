"""Opt-in observation of the bundle-adjustment optimizers. Read-only: never changes the numbers.

`OptimizerObserver` wraps the `fun`/`jac` callables passed to `scipy.optimize.least_squares`
and supplies a `callback` so that each accepted `trf` iteration is recorded as a `TraceRow`.
Wrapping is purely observational -- the wrapped callables return the inner results unchanged,
and passing an observer must not alter `result.x` or `result.cost` in any way.

Column layout note: `optimality` here is an *unconstrained* proxy, `||J^T f||_inf`, computed
from the residual/Jacobian pair at each accepted step. It intentionally does NOT match the
`optimality` scipy reports on the final `OptimizeResult`, which applies Coleman-Li bound
scaling that this proxy skips. When the Jacobian is computed via `"2-point"` (i.e.
`use_sparse_jacobian=False`), there is no `jac` callable to wrap, so `optimality` is `nan`
for every row.
"""

from __future__ import annotations

import csv
import logging
import math
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import numpy as np
from numpy.typing import NDArray

from aquacal.io.internals import warn_if_overwriting

if TYPE_CHECKING:
    from aquacal.validation.conditioning import ConditioningReport

logger = logging.getLogger(__name__)

TRACE_CSV_HEADER = [
    "iteration",
    "n_fev",
    "cost",
    "step_norm",
    "optimality",
    "water_z",
    "tilt_rx",
    "tilt_ry",
]


@dataclass
class TraceRow:
    """One accepted `trf` iteration's worth of per-iteration optimizer diagnostics.

    Attributes:
        iteration: scipy's accepted-iteration count (`intermediate_result.nit`).
        n_fev: Cumulative residual-function evaluation count.
        cost: `0.5 * sum(fun**2)` at this iteration (scipy's convention).
        step_norm: Euclidean norm of `x_i - x_{i-1}`; `0.0` for the first row.
        optimality: Unconstrained `||J^T f||_inf` proxy; `nan` if unavailable
            (e.g. `jac="2-point"` or a stale residual/Jacobian pair).
        water_z: Global water-surface Z parameter sliced from `x`.
        tilt_rx: Reference-camera tilt about X, or `nan` when `normal_fixed=True`.
        tilt_ry: Reference-camera tilt about Y, or `nan` when `normal_fixed=True`.
    """

    iteration: int
    n_fev: int
    cost: float
    step_norm: float
    optimality: float
    water_z: float
    tilt_rx: float
    tilt_ry: float


def build_parameter_labels(
    camera_order: list[str],
    frame_order: list[int],
    reference_camera: str,
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
) -> list[str]:
    """Build a human-readable name for each entry of the packed parameter vector.

    Mirrors `_optim_common.pack_params`'s layout exactly (same argument order, same
    conditional blocks) so that `labels[i]` names `x[i]` for any `x` produced by
    `pack_params` with the same arguments. This is the only way the conditioning
    correlation matrix's rows/columns become readable -- e.g. finding `water_z`
    and each camera's `_tvec_z` to inspect the camera-height / water_z coupling.

    Args:
        camera_order: Ordered list of camera names, matching `pack_params`.
        frame_order: Ordered list of frame indices, matching `pack_params`.
        reference_camera: Name of the reference camera (skipped in extrinsics
            packing).
        refine_intrinsics: Whether intrinsics are included in the parameter
            vector.
        normal_fixed: If False, the first two labels are the reference camera's
            tilt rx/ry.

    Returns:
        List of parameter names, one per entry of the packed vector, in the
        same order `pack_params` emits values.
    """
    labels: list[str] = []

    if not normal_fixed:
        labels.extend(["ref_tilt_rx", "ref_tilt_ry"])

    for cam_name in camera_order:
        if cam_name == reference_camera:
            continue
        labels.extend(
            [
                f"{cam_name}_rvec_x",
                f"{cam_name}_rvec_y",
                f"{cam_name}_rvec_z",
                f"{cam_name}_tvec_x",
                f"{cam_name}_tvec_y",
                f"{cam_name}_tvec_z",
            ]
        )

    labels.append("water_z")

    for frame_idx in frame_order:
        labels.extend(
            [
                f"frame{frame_idx}_rvec_x",
                f"frame{frame_idx}_rvec_y",
                f"frame{frame_idx}_rvec_z",
                f"frame{frame_idx}_tvec_x",
                f"frame{frame_idx}_tvec_y",
                f"frame{frame_idx}_tvec_z",
            ]
        )

    if refine_intrinsics:
        for cam_name in camera_order:
            labels.extend(
                [
                    f"{cam_name}_fx",
                    f"{cam_name}_fy",
                    f"{cam_name}_cx",
                    f"{cam_name}_cy",
                ]
            )

    return labels


class OptimizerObserver:
    """Read-only observer for a single `least_squares` bundle-adjustment call.

    Attach via `wrap_fun`/`wrap_jac`/`callback` before calling `least_squares`, then call
    `on_solution(result)` afterward and `write_trace_csv(path)` to persist the trace.

    Never retains a reference to a Jacobian matrix -- only a scalar `optimality` value is
    cached between the `jac` wrapper and the `callback`.
    """

    def __init__(
        self,
        stage: str,
        water_z_index: int | None = None,
        normal_fixed: bool = True,
        conditioning: bool = False,
    ) -> None:
        """Create an observer for one bundle-adjustment stage.

        Args:
            stage: Human-readable stage name (e.g. "stage3", "stage3_rerun", "stage4"),
                used only for logging/debugging context.
            water_z_index: Index of `water_z` within the packed parameter vector `x`.
                If `None`, `water_z`/`tilt_rx`/`tilt_ry` are recorded as `nan`. Set via
                `configure_layout` if not known at construction time.
            normal_fixed: If `False`, `x[0]`/`x[1]` are the reference camera's tilt
                rx/ry and are recorded; if `True`, both are `nan`.
            conditioning: If `True`, `on_solution` computes Jacobian conditioning
                diagnostics (singular-value spectrum, condition number, parameter
                correlation) from `result.jac`. If `False`, `on_solution` is a no-op.
        """
        self.stage = stage
        self.water_z_index = water_z_index
        self.normal_fixed = normal_fixed
        self.conditioning = conditioning
        self.parameter_labels: list[str] | None = None
        self.conditioning_report: ConditioningReport | None = None

        self.rows: list[TraceRow] = []

        self._x_prev: NDArray[np.float64] | None = None
        self._f_cached: NDArray[np.float64] | None = None
        self._x_cached: NDArray[np.float64] | None = None
        self._last_optimality: float = math.nan

    def configure_layout(
        self,
        water_z_index: int,
        normal_fixed: bool,
        parameter_labels: list[str] | None = None,
    ) -> None:
        """Set the parameter-vector layout indices used to slice interface params.

        Args:
            water_z_index: Index of `water_z` within the packed parameter vector.
            normal_fixed: Whether the reference camera's tilt is fixed (excluded
                from the parameter vector).
            parameter_labels: Optional per-parameter names (from
                `build_parameter_labels`) used to label the conditioning
                correlation matrix. Ignored unless `conditioning=True`.
        """
        self.water_z_index = water_z_index
        self.normal_fixed = normal_fixed
        self.parameter_labels = parameter_labels

    def wrap_fun(self, fun: Callable) -> Callable:
        """Wrap a residual function, caching its result for the optimality proxy.

        Args:
            fun: The inner residual function, called as `fun(x, *args, **kwargs)`.

        Returns:
            A wrapper with the same call signature that returns the inner result
            unchanged, after caching a copy of `(x, residuals)`.
        """

        @wraps(fun)
        def wrapped(x, *args, **kwargs):
            result = fun(x, *args, **kwargs)
            self._x_cached = np.array(x, copy=True)
            self._f_cached = np.array(result, copy=True)
            return result

        return wrapped

    def wrap_jac(self, jac):
        """Wrap a Jacobian callable, computing the optimality proxy as a side effect.

        Args:
            jac: The inner Jacobian callable (`jac(x, *args, **kwargs) -> J`), or the
                string `"2-point"` when finite differences are used instead of an
                explicit callable.

        Returns:
            A wrapper with the same call signature that returns `J` unchanged, after
            computing and caching `||J^T f||_inf` (or leaving it `nan` if the cached
            residual does not match `x`). If `jac` is a string, it is returned
            unchanged and `optimality` stays `nan` for every row.
        """
        if isinstance(jac, str):
            return jac

        @wraps(jac)
        def wrapped(x, *args, **kwargs):
            J = jac(x, *args, **kwargs)
            if self._f_cached is not None and np.array_equal(x, self._x_cached):
                if hasattr(J, "dot") and not isinstance(J, np.ndarray):
                    # Sparse matrix: J.T.dot(f) avoids densifying J.
                    grad = J.T.dot(self._f_cached)
                else:
                    grad = J.T @ self._f_cached
                self._last_optimality = float(np.linalg.norm(grad, np.inf))
            else:
                self._last_optimality = math.nan
            return J

        return wrapped

    def callback(self, intermediate_result) -> None:
        """scipy `least_squares(callback=...)` hook; fired once per accepted iteration.

        Args:
            intermediate_result: `scipy.optimize.OptimizeResult` with `x`, `fun`,
                `nit`, `nfev`, `cost` populated (per the scipy 1.16+ `callback`
                contract). No other fields are guaranteed to be present.
        """
        x = np.asarray(intermediate_result.x)

        if self._x_prev is None:
            step_norm = 0.0
        else:
            step_norm = float(np.linalg.norm(x - self._x_prev))
        self._x_prev = np.array(x, copy=True)

        water_z = math.nan
        tilt_rx = math.nan
        tilt_ry = math.nan
        if self.water_z_index is not None:
            water_z = float(x[self.water_z_index])
            if not self.normal_fixed:
                tilt_rx = float(x[0])
                tilt_ry = float(x[1])

        self.rows.append(
            TraceRow(
                iteration=int(intermediate_result.nit),
                n_fev=int(intermediate_result.nfev),
                cost=float(intermediate_result.cost),
                step_norm=step_norm,
                optimality=self._last_optimality,
                water_z=water_z,
                tilt_rx=tilt_rx,
                tilt_ry=tilt_ry,
            )
        )

    def on_solution(self, result) -> None:
        """Compute Jacobian conditioning diagnostics at the solution, if enabled.

        Called once, immediately after `least_squares` returns, while `result.jac`
        is still alive in the caller's scope. When `self.conditioning` is `True`,
        computes a `ConditioningReport` via `compute_conditioning` and stores it
        on `self.conditioning_report` -- only that small `(n, n)` report survives;
        `result`/`result.jac` are never retained as attributes on this observer.

        Args:
            result: The final `scipy.optimize.OptimizeResult` from `least_squares`.

        Raises:
            ConditioningMemoryError: Re-raised (with this observer's stage name
                prefixed to the message) if the conditioning computation's
                analytic memory pre-check refuses the allocation. This
                propagates all the way out -- the caller must not narrow the
                metric to keep the run alive.
        """
        if not self.conditioning:
            return

        # Local import: avoids a calibration -> validation import at module load.
        from aquacal.validation.conditioning import (
            ConditioningMemoryError,
            compute_conditioning,
        )

        try:
            self.conditioning_report = compute_conditioning(
                result.jac,
                parameter_names=self.parameter_labels,
            )
        except ConditioningMemoryError as exc:
            raise ConditioningMemoryError(f"[{self.stage}] {exc}") from exc

    def write_trace_csv(self, path: Path) -> None:
        """Write the captured per-iteration trace to a CSV file.

        Args:
            path: Destination file path. Parent directories are created if needed.
                If `path` already exists, a warning is logged before overwriting.
        """
        path = Path(path)
        warn_if_overwriting(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self.rows:
            logger.warning(
                "OptimizerObserver for stage '%s' recorded zero accepted "
                "iterations; writing header-only trace to %s.",
                self.stage,
                path,
            )

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(TRACE_CSV_HEADER)
            for row in self.rows:
                writer.writerow(
                    [
                        row.iteration,
                        row.n_fev,
                        row.cost,
                        row.step_norm,
                        row.optimality,
                        row.water_z,
                        row.tilt_rx,
                        row.tilt_ry,
                    ]
                )
