"""Declared-constants table for E3 tier 1 (D-18, EXP-07).

This module OWNS the declared-constants table for E3 tier 1. `experiments/e3_derived_quantities.py`
(plan 19.2-05) imports `DECLARED_CONSTANTS` from here and only *renders* it into
`code_constants.csv` -- it never re-declares a row. The table is declared exactly once, in
`tests/`, so CI is the gate that breaks first when a library default changes, rather than
letting the supplement's prose silently drift out of sync with the shipped code.

Every declared value below is checked against a value read LIVE from the library -- by calling
a function, by reading a signature default, or (for the two literals that expose neither) by an
anchored regex over the function's own source text. No row is ever compared against a hardcoded
source line number (19.2-RESEARCH.md Pitfall 1): line numbers shift on every unrelated edit and
would silently stop verifying anything.

Import precondition (review L2): `tests/__init__.py` exists but `tests/unit/__init__.py` does
NOT, so `from tests.unit.test_experiments_e3_constants import DECLARED_CONSTANTS` resolves only
via PEP 420 namespace-portion semantics, and only when the repository root is importable (i.e.
on `sys.path`). Plan 19.2-05's script bootstraps `sys.path` from `__file__` rather than relying
on the working directory. Do NOT create `tests/unit/__init__.py` to "fix" this -- adding a
package marker under an existing rootdir changes pytest's collection semantics for the whole
directory, which is a larger blast radius than the import it would tidy.
"""

from __future__ import annotations

import inspect
import re
import sys
from typing import Callable, NamedTuple

import numpy as np
import pytest

from aquacal.calibration._observability import (
    SolverDiagnostics,
    build_parameter_labels,
)
from aquacal.calibration._optim_common import (
    build_bounds,
    compute_residuals,
    make_sparse_jacobian_func,
)
from aquacal.calibration.interface_estimation import (
    optimize_interface,
    register_auxiliary_camera,
)
from aquacal.calibration.refinement import joint_refinement
from aquacal.config.schema import (
    BoardConfig,
    CameraExtrinsics,
    CameraIntrinsics,
)
from aquacal.core.board import BoardGeometry
from aquacal.core.refractive_geometry import _refractive_project_newton

sys.path.insert(0, ".")
from tests.synthetic.ground_truth import generate_synthetic_detections

# --- Live-value accessors -------------------------------------------------
#
# Each accessor is a zero-argument callable returning the CURRENT value read
# from the library. None of them accept or embed a line number.


def _water_z_bounds() -> tuple[float, float]:
    """`build_bounds`'s water_z slot, located by label (not by offset math)."""
    camera_order = ["cam0", "cam1"]
    frame_order = [0]
    lower, upper = build_bounds(camera_order, frame_order, reference_camera="cam0")
    labels = build_parameter_labels(camera_order, frame_order, reference_camera="cam0")
    i = labels.index("water_z")
    return (float(lower[i]), float(upper[i]))


def _refined_intrinsics_bounds_frac() -> tuple[float, float]:
    """`build_bounds`'s fx slot under `refine_intrinsics=True`, as a fraction of nominal fx."""
    camera_order = ["cam0", "cam1"]
    frame_order = [0]
    fx_nominal = 1000.0
    base_intrinsics = {
        cam: CameraIntrinsics(
            K=np.array(
                [[fx_nominal, 0, 320], [0, fx_nominal, 240], [0, 0, 1]],
                dtype=np.float64,
            ),
            dist_coeffs=np.zeros(5, dtype=np.float64),
            image_size=(640, 480),
        )
        for cam in camera_order
    }
    lower, upper = build_bounds(
        camera_order,
        frame_order,
        reference_camera="cam0",
        base_intrinsics=base_intrinsics,
        refine_intrinsics=True,
    )
    labels = build_parameter_labels(
        camera_order, frame_order, reference_camera="cam0", refine_intrinsics=True
    )
    i = labels.index("cam0_fx")
    return (float(lower[i] / fx_nominal), float(upper[i] / fx_nominal))


def _huber_f_scale_signature_defaults() -> tuple[float, float]:
    """Both signature-default Huber sites: Stage 3's and Stage 4's `loss_scale`."""
    stage3_default = (
        inspect.signature(optimize_interface).parameters["loss_scale"].default
    )
    stage4_default = (
        inspect.signature(joint_refinement).parameters["loss_scale"].default
    )
    return (float(stage3_default), float(stage4_default))


def _aux_registration_f_scale() -> float:
    """The THIRD Huber site: a bare `f_scale=` literal inside `register_auxiliary_camera`.

    No callable or signature surface exposes this value -- it is passed directly to
    `least_squares` inside the function body -- so it is read by an anchored regex over the
    function's own source text (review M10).
    """
    source = inspect.getsource(register_auxiliary_camera)
    match = re.search(r"f_scale=(\d+\.?\d*)", source)
    assert match is not None, "f_scale= literal not found in register_auxiliary_camera"
    return float(match.group(1))


def _invalid_tir_penalty() -> float:
    """The 100 px invalid/TIR penalty inside `compute_residuals`.

    No callable or signature surface exposes this value -- it is a bare assignment to a local
    array -- so it is read by an anchored regex over the function's own source text.
    """
    source = inspect.getsource(compute_residuals)
    match = re.search(r"diff\[invalid\]\s*=\s*(\d+\.?\d*)", source)
    assert match is not None, "diff[invalid] = literal not found in compute_residuals"
    return float(match.group(1))


def _newton_tolerance() -> float:
    return float(
        inspect.signature(_refractive_project_newton).parameters["tolerance"].default
    )


def _newton_max_iterations() -> int:
    return int(
        inspect.signature(_refractive_project_newton)
        .parameters["max_iterations"]
        .default
    )


def _dense_threshold() -> int:
    return int(
        inspect.signature(make_sparse_jacobian_func)
        .parameters["dense_threshold"]
        .default
    )


def _solver_tolerances() -> tuple[float, float, float]:
    """Live BENCH-06 tolerances: run one minimal `optimize_interface` solve and read them
    back off a `SolverDiagnostics` out-parameter, rather than trusting the supplement's prose.

    The scenario mirrors `tests/unit/test_benchmark.py`'s `real_solver_diagnostics` fixture --
    a tiny 3-camera, 3-frame synthetic problem -- deliberately kept minimal so this stays well
    under a second.
    """
    K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros(5, dtype=np.float64)
    intrinsics = {
        cam: CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        )
        for cam in ("cam0", "cam1", "cam2")
    }
    extrinsics = {
        "cam0": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64), t=np.zeros(3, dtype=np.float64)
        ),
        "cam1": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64), t=np.array([0.1, 0.0, 0.0], dtype=np.float64)
        ),
        "cam2": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64), t=np.array([0.0, 0.1, 0.0], dtype=np.float64)
        ),
    }
    distances = {"cam0": 0.15, "cam1": 0.15, "cam2": 0.15}
    board = BoardGeometry(
        BoardConfig(
            squares_x=6,
            squares_y=5,
            square_size=0.04,
            marker_size=0.03,
            dictionary="DICT_4X4_50",
        )
    )
    board_poses = []
    for i in range(3):
        x_offset = 0.05 * (i - 1)
        y_offset = 0.02 * i
        board_poses.append(
            {
                "frame_idx": i,
                "rvec": np.array([0.1 * (i % 3), 0.1 * (i % 2), 0.0], dtype=np.float64),
                "tvec": np.array([x_offset, y_offset, 0.4], dtype=np.float64),
            }
        )
    from aquacal.config.schema import BoardPose

    poses = [BoardPose(**p) for p in board_poses]

    np.random.seed(42)
    detections = generate_synthetic_detections(
        intrinsics,
        extrinsics,
        distances,
        board,
        poses,
        noise_std=0.5,
        min_corners=4,
    )
    diag = SolverDiagnostics()
    optimize_interface(
        detections=detections,
        intrinsics=intrinsics,
        initial_extrinsics=extrinsics,
        board=board,
        reference_camera="cam0",
        verbose=0,
        use_sparse_jacobian=True,
        diagnostics_out=diag,
    )
    return (diag.ftol, diag.xtol, diag.gtol)


class DeclaredConstant(NamedTuple):
    """One row of the E3 tier 1 declared-constants table.

    Attributes:
        key: Stable snake_case identifier, used as the CSV's primary key.
        claim: The supplement's own sentence, quoted from `19.2-SOURCE-BRIEF.md` Section E3
            Tier 1 (or, for `dense_threshold_elements`, from `19.2-CONTEXT.md` D-15's quote of
            the source worklist).
        source: A dotted module path plus symbol. Never a line number.
        declared_value: The value the supplement asserts.
        read_via: One of `"call"`, `"signature_default"`, or `"source_regex"`.
        live: A zero-argument callable returning the current value from the library.
    """

    key: str
    claim: str
    source: str
    declared_value: object
    read_via: str
    live: Callable[[], object]


DECLARED_CONSTANTS: tuple[DeclaredConstant, ...] = (
    DeclaredConstant(
        key="water_z_bounds_m",
        claim="`water_z` bounded to `[0.01, 2.0] m`",
        source="aquacal.calibration._optim_common.build_bounds",
        declared_value=(0.01, 2.0),
        read_via="call",
        live=_water_z_bounds,
    ),
    DeclaredConstant(
        key="refined_intrinsics_bounds_frac",
        claim="refined intrinsics bounded to 50-200% of their nominal value",
        source="aquacal.calibration._optim_common.build_bounds",
        declared_value=(0.5, 2.0),
        read_via="call",
        live=_refined_intrinsics_bounds_frac,
    ),
    DeclaredConstant(
        key="huber_f_scale_px",
        claim="Huber robust loss, `f_scale = 1.0 px`",
        source=(
            "aquacal.calibration.interface_estimation.optimize_interface;"
            "aquacal.calibration.refinement.joint_refinement"
        ),
        declared_value=(1.0, 1.0),
        read_via="signature_default",
        live=_huber_f_scale_signature_defaults,
    ),
    DeclaredConstant(
        key="aux_registration_f_scale_px",
        claim="Huber robust loss, `f_scale = 1.0 px` (third site, hardcoded)",
        source="aquacal.calibration.interface_estimation.register_auxiliary_camera",
        declared_value=1.0,
        read_via="source_regex",
        live=_aux_registration_f_scale,
    ),
    DeclaredConstant(
        key="invalid_tir_penalty_px",
        claim="Invalid/TIR configurations take a fixed 100 px penalty",
        source="aquacal.calibration._optim_common.compute_residuals",
        declared_value=100.0,
        read_via="source_regex",
        live=_invalid_tir_penalty,
    ),
    DeclaredConstant(
        key="newton_tolerance_m",
        claim="Newton root-find tolerance `1e-9 m`",
        source="aquacal.core.refractive_geometry._refractive_project_newton",
        declared_value=1e-9,
        read_via="signature_default",
        live=_newton_tolerance,
    ),
    DeclaredConstant(
        key="newton_max_iterations",
        claim="Newton root-find converges within `max_iterations = 10`",
        source="aquacal.core.refractive_geometry._refractive_project_newton",
        declared_value=10,
        read_via="signature_default",
        live=_newton_max_iterations,
    ),
    DeclaredConstant(
        key="dense_threshold_elements",
        claim=(
            "`make_sparse_jacobian_func` returns a dense Jacobian below a "
            "~4 GiB element-count threshold"
        ),
        source="aquacal.calibration._optim_common.make_sparse_jacobian_func",
        declared_value=500_000_000,
        read_via="signature_default",
        live=_dense_threshold,
    ),
    DeclaredConstant(
        key="solver_tolerances",
        claim="termination tolerances of `1e-8` on the cost, parameters, and gradient",
        source=(
            "aquacal.calibration.interface_estimation.optimize_interface;"
            "aquacal.calibration.refinement.joint_refinement"
        ),
        declared_value=(1e-8, 1e-8, 1e-8),
        read_via="call",
        live=_solver_tolerances,
    ),
)


class TestDeclaredConstantsMatchLiveValues:
    """Every declared row must equal a value read live from the library (D-18)."""

    @pytest.mark.parametrize(
        "entry", DECLARED_CONSTANTS, ids=[e.key for e in DECLARED_CONSTANTS]
    )
    def test_declared_value_matches_live_read(self, entry: DeclaredConstant):
        live_value = entry.live()
        if isinstance(entry.declared_value, tuple):
            # Exact, element-wise equality -- every declared value here is a literal the
            # library assigns directly (bound constants, signature defaults, or a value
            # read straight back off SolverDiagnostics), so no float comparison here
            # genuinely requires a tolerance.
            assert isinstance(live_value, tuple)
            assert len(live_value) == len(entry.declared_value)
            for live_item, declared_item in zip(live_value, entry.declared_value):
                assert live_item == declared_item, entry.key
        else:
            assert live_value == entry.declared_value, entry.key


class TestDeclaredConstantsTableStructure:
    """Structural invariants over the table itself (`pytest -k declaration`)."""

    def test_declaration_has_exactly_nine_unique_entries(self):
        assert len(DECLARED_CONSTANTS) == 9
        keys = [entry.key for entry in DECLARED_CONSTANTS]
        assert len(set(keys)) == 9

    def test_declaration_sources_never_cite_a_line_number(self):
        for entry in DECLARED_CONSTANTS:
            assert re.search(r":\d+", entry.source) is None, entry.key

    def test_declaration_read_via_values_are_valid_and_source_regex_count_is_two(self):
        allowed = {"call", "signature_default", "source_regex"}
        for entry in DECLARED_CONSTANTS:
            assert entry.read_via in allowed, entry.key
        source_regex_count = sum(
            1 for entry in DECLARED_CONSTANTS if entry.read_via == "source_regex"
        )
        assert source_regex_count == 2


class TestDeclaredConstantsRowsAreWellFormed:
    """Every row's claim and declared value are non-empty."""

    @pytest.mark.parametrize(
        "entry", DECLARED_CONSTANTS, ids=[e.key for e in DECLARED_CONSTANTS]
    )
    def test_claim_and_declared_value_are_non_empty(self, entry: DeclaredConstant):
        assert isinstance(entry.claim, str) and entry.claim != ""
        assert entry.declared_value is not None
        if isinstance(entry.declared_value, tuple):
            assert len(entry.declared_value) > 0
