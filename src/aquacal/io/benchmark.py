"""Environment/peak-memory capture and benchmark.json assembly (BENCH-01..04).

`capture_environment`/`capture_peak_memory` are pure, side-effect-free capture
primitives: they read process/OS/dependency state and return a plain dict of
natively-typed values. `assemble_benchmark_record`/`write_benchmark_json`
build and persist the machine-readable `benchmark.json` record BENCH-04
requires from values the pipeline already computed -- neither function
recomputes anything (D-06) or invents metrics a run did not produce (D-14,
D-15).

`capture_environment`/`capture_peak_memory` are designed to never raise,
regardless of platform or which optional dependencies are installed, because
a benchmark measurement must never be the reason a calibration run fails
(D-05).
"""

from __future__ import annotations

import dataclasses
import importlib.metadata
import json
import logging
import os
import platform
import subprocess
import tomllib
import tracemalloc
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
import scipy

from aquacal.io.internals import warn_if_overwriting

if TYPE_CHECKING:
    from aquacal.calibration._observability import SolverDiagnostics

logger = logging.getLogger(__name__)

_MAX_GIT_PARENT_LEVELS = 6


def _find_git_root(start: Path) -> Path | None:
    """Walk upward from `start` looking for a `.git` directory.

    Args:
        start: Directory to begin the search from.

    Returns:
        The first ancestor directory (including `start`) containing a
        `.git` entry, or `None` if none is found within
        `_MAX_GIT_PARENT_LEVELS` parent levels.
    """
    current = start
    for _ in range(_MAX_GIT_PARENT_LEVELS + 1):
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def capture_environment(repo_hint_path: Path | None = None) -> dict:
    """Capture a best-effort environment snapshot for benchmark.json.

    Never raises: every external call (the optional `psutil` import, the
    `git rev-parse HEAD` subprocess) is wrapped in its own `try/except` so a
    partial record is always produced rather than aborting the calibration
    run that requested it (D-05).

    Args:
        repo_hint_path: Directory to run `git rev-parse HEAD` from. Defaults
            to walking upward from this module's own file looking for a
            `.git` directory, bounded to `_MAX_GIT_PARENT_LEVELS` parent
            levels. A pip-installed package run outside any git checkout has
            no `.git` at all -- the expected, common case this degrades
            gracefully for.

    Returns:
        Plain dict with every value already cast to a native Python type
        (`str`/`int`/`None`), matching the numpy-to-JSON cast precedent in
        `aquacal.validation.conditioning`:
            - `aquacal_version` (str): always a non-empty string. Read from
              INSTALLED distribution metadata, which an editable install
              refreshes only at `pip install -e .` time.
            - `aquacal_version_declared` (str | None): the `version` declared
              in the checkout's `pyproject.toml`, or `None` when no checkout
              is reachable. Present so a reader diffing two artifacts can SEE
              a stale editable install rather than infer it: when this differs
              from `aquacal_version`, the code that ran was the working tree
              and `aquacal_version` names a different, older release.
            - `python_version` (str)
            - `numpy_version` (str)
            - `scipy_version` (str)
            - `opencv_version` (str)
            - `os` (str): e.g. `"Windows 11"`.
            - `cpu_model` (str): raw `platform.processor()` string.
            - `cpu_count_logical` (int | None): `None` when `psutil` is
              unavailable.
            - `ram_total_bytes` (int | None): `None` when `psutil` is
              unavailable.
            - `git_sha` (str | None): 40-character hex string, or `None`.
            - `git_sha_source` (str): `"git_rev_parse"` or `"unavailable"`.
    """
    env = {
        "aquacal_version": "unknown",
        "aquacal_version_declared": None,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "opencv_version": cv2.__version__,
        "os": f"{platform.system()} {platform.release()}",
        "cpu_model": platform.processor(),
        "cpu_count_logical": None,
        "ram_total_bytes": None,
        "git_sha": None,
        "git_sha_source": "unavailable",
    }

    try:
        env["aquacal_version"] = importlib.metadata.version("aquacal")
    except Exception:
        logger.debug(
            "Could not resolve aquacal_version for benchmark environment capture."
        )

    # One repo root, used for both the declared-version read below and the
    # `git rev-parse HEAD` call further down -- the artifact must not describe
    # two different checkouts.
    cwd = (
        repo_hint_path
        if repo_hint_path is not None
        else _find_git_root(Path(__file__).resolve().parent)
    )

    try:
        pyproject = Path(cwd) / "pyproject.toml"  # type: ignore[arg-type]
        env["aquacal_version_declared"] = tomllib.loads(
            pyproject.read_text(encoding="utf-8")
        )["project"]["version"]
    except Exception:
        logger.debug(
            "aquacal_version_declared unavailable (no reachable checkout, or "
            "pyproject.toml could not be parsed)."
        )

    try:
        import psutil

        env["cpu_count_logical"] = psutil.cpu_count(logical=True)
        env["ram_total_bytes"] = int(psutil.virtual_memory().total)
    except Exception:
        logger.debug(
            "psutil unavailable; cpu_count_logical/ram_total_bytes left as None."
        )

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        env["git_sha"] = result.stdout.strip()
        env["git_sha_source"] = "git_rev_parse"
    except Exception:
        logger.debug(
            "git_sha unavailable (not a git checkout, or git is not installed)."
        )

    return env


def _linux_vmhwm_bytes() -> int | None:
    """Read this process's peak resident set size from `/proc/<pid>/status`.

    Returns:
        The `VmHWM` value in bytes, or `None` if the file cannot be read or
        does not contain a `VmHWM` line.
    """
    try:
        with open(f"/proc/{os.getpid()}/status") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


_NULL_COMMIT_FIELDS = {
    "commit_current_bytes": None,
    "commit_peak_bytes": None,
    "ram_total_bytes": None,
}


def capture_peak_memory() -> dict:
    """Capture a labelled peak-memory reading, safe to call repeatedly.

    Dispatches on `platform.system()` to the cheapest true high-water-mark
    read available: Windows uses `psutil`'s monotonic `peak_wset` field;
    Linux reads `/proc/<pid>/status`'s `VmHWM` line directly (psutil exposes
    no peak-RSS equivalent on Linux -- giampaolo/psutil#1096, #1540); other
    platforms with `psutil` installed take a single instantaneous RSS
    sample (honestly labelled as a snapshot, not a true peak); environments
    without `psutil` fall back to `tracemalloc`'s traced-peak.

    Every mode is a single synchronous read: no background thread, no
    polling loop, no `start()`/`stop()` pairing required from the caller.
    This function holds no module-level or instance state between calls
    beyond `tracemalloc`'s own already-running global trace state (queried,
    never reset). It is therefore safe to call at every stage boundary of a
    single run, and each call's `peak_bytes` is monotonically
    non-decreasing across calls within one process for every OS-native mode
    (D-18) -- this is the property per-stage attribution depends on.

    Never raises: the entire dispatch is wrapped in `try/except`, degrading
    to `{"peak_bytes": None, "mode": "unavailable", "commit_current_bytes":
    None, "commit_peak_bytes": None, "ram_total_bytes": None}` on any
    unexpected error, because a memory measurement must never abort a
    calibration run.

    `peak_bytes` alone cannot distinguish a clean measurement from one
    where the OS silently paged a near-limit process to disk (D-33 gap 3):
    on Windows, `peak_bytes`/`mode` describe the *resident* working set
    (`peak_wset`), which paging caps near the physical ceiling while the
    process's true *commit* charge keeps climbing. `commit_current_bytes`/
    `commit_peak_bytes` -- read from the same `psutil` call alongside
    `ram_total_bytes` -- let a reader detect that divergence rather than
    inferring it.

    Returns:
        Dict with five keys:
            - `peak_bytes` (int | None): the resident high-water-mark
              reading, in bytes. Unchanged in meaning and value from before
              this function grew the commit/virtual fields below.
            - `mode` (str): one of `"psutil_peak_wset"`,
              `"proc_status_vmhwm"`, `"tracemalloc_python_heap"`,
              `"psutil_rss_sampled"`, or `"unavailable"`. Distinguishes a
              true OS-maintained high-water mark from the weaker
              instantaneous `"psutil_rss_sampled"` fallback -- never
              conflate the two. Unchanged vocabulary.
            - `commit_current_bytes` (int | None): the process's current
              commit/pagefile charge, in bytes. Populated only on Windows
              (`psutil.Process().memory_full_info().pagefile`); `None`
              everywhere else, including on any failure.
            - `commit_peak_bytes` (int | None): the process's peak
              commit/pagefile charge, in bytes. Populated only on Windows
              (`...memory_full_info().peak_pagefile`); `None` everywhere
              else.
            - `ram_total_bytes` (int | None): the machine's total physical
              RAM, in bytes. Populated only on Windows
              (`psutil.virtual_memory().total`); `None` everywhere else.
    """
    try:
        system = platform.system()

        if system == "Linux":
            vmhwm_bytes = _linux_vmhwm_bytes()
            if vmhwm_bytes is not None:
                return {
                    "peak_bytes": vmhwm_bytes,
                    "mode": "proc_status_vmhwm",
                    **_NULL_COMMIT_FIELDS,
                }

        if system == "Windows":
            try:
                import psutil

                full_info = psutil.Process().memory_full_info()
                ram_total_bytes = int(psutil.virtual_memory().total)
                return {
                    "peak_bytes": int(full_info.peak_wset),
                    "mode": "psutil_peak_wset",
                    "commit_current_bytes": int(full_info.pagefile),
                    "commit_peak_bytes": int(full_info.peak_pagefile),
                    "ram_total_bytes": ram_total_bytes,
                }
            except ImportError:
                logger.debug(
                    "psutil unavailable on Windows; falling back to tracemalloc."
                )
        elif system != "Linux":
            try:
                import psutil

                rss = psutil.Process().memory_info().rss
                return {
                    "peak_bytes": int(rss),
                    "mode": "psutil_rss_sampled",
                    **_NULL_COMMIT_FIELDS,
                }
            except ImportError:
                logger.debug(
                    "psutil unavailable on %s; falling back to tracemalloc.", system
                )

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        _, peak_bytes = tracemalloc.get_traced_memory()
        return {
            "peak_bytes": int(peak_bytes),
            "mode": "tracemalloc_python_heap",
            **_NULL_COMMIT_FIELDS,
        }
    except Exception:
        logger.debug(
            "capture_peak_memory() failed unexpectedly; degrading to unavailable."
        )
        return {"peak_bytes": None, "mode": "unavailable", **_NULL_COMMIT_FIELDS}


_STAGES_WITH_NO_SOLVER_DIAGNOSTICS_REASON = (
    "no in-scope least_squares solver diagnostics were captured for this stage"
)


def _resolve_stage_seconds(stage_name, timings):
    """Resolve a stage block's wall time, honestly, when the diagnostics stage
    key does not have a 1:1 entry in ``timings``.

    Returns ``(seconds, reason)``. ``reason`` is non-None only when ``seconds``
    is None for a *known* reason (D-15: null-with-reason, never a silent null).

    - Exact match in ``timings`` (the common case): the measured wall time.
    - ``stage3_rerun``: its wall time is folded into
      ``stage3_interface_optimization`` in the pipeline, so there is no separate
      number to report.
    - ``auxiliary_registration_<cam>``: the pipeline times auxiliary
      registration in aggregate under ``auxiliary_registration``, not per camera.
    """
    if stage_name in timings:
        return timings[stage_name], None
    if stage_name == "stage3_rerun":
        return None, "wall time is folded into stage3_interface_optimization"
    if stage_name.startswith("auxiliary_registration_"):
        return None, (
            "per-camera wall time is not measured separately; see the "
            "auxiliary_registration aggregate boundary"
        )
    return None, None


def _to_native(value):
    """Recursively cast `numpy` scalars/arrays to native JSON-safe Python types.

    The JSON-serialization boundary of last resort (Research Pitfall 3):
    `capture_solver_diagnostics` already casts every `SolverDiagnostics` field
    at capture time, and pipeline call sites are expected to pass already-cast
    values into `problem_shape`/`solver_config`/`accuracy`, but this function
    must not assume every value arrived pre-cast -- any `np.generic` scalar
    (`np.float64`, `np.int64`, ...) or `np.ndarray` reaching here, at any
    nesting depth inside a dict/list/tuple, is coerced before `json.dump`
    ever sees it.

    Args:
        value: Any value, possibly a numpy scalar/array or a container
            (dict/list/tuple) nesting one.

    Returns:
        A JSON-safe equivalent: `numpy` scalars become Python `int`/`float`/
        `bool` via `.item()`, `numpy` arrays become nested lists via
        `.tolist()`, dicts/lists/tuples are recursed into, everything else is
        returned unchanged.
    """
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {k: _to_native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_native(v) for v in value]
    return value


def assemble_benchmark_record(
    *,
    schema_version: int = 1,
    problem_shape: dict,
    timings: dict,
    diagnostics: dict[str, "SolverDiagnostics"],
    solver_config: dict,
    accuracy: dict,
    environment: dict,
    memory_readings: dict | None = None,
) -> dict:
    """Assemble the full `benchmark.json` record (BENCH-01, BENCH-03, BENCH-04).

    Pure function -- no I/O. Returns a dict in which every value is already a
    native Python type, verified by `json.dumps` round-tripping cleanly.

    Args:
        schema_version: Integer schema version (D-04), default `1`.
        problem_shape: Caller-supplied dict describing the run's problem size
            (e.g. `n_cameras`, `n_frames_calibration`, `n_frames_holdout`).
            Passed through unmodified.
        timings: The pipeline's `timings` dict (wall-clock seconds per stage,
            keyed by the settled stage vocabulary -- D-03). Used to attach a
            `"seconds"` field to each stage block.
        diagnostics: Dict keyed by stage name, mapping to the
            `SolverDiagnostics` instance captured for that stage's
            `least_squares` call. A stage this run did not execute is simply
            absent from this dict (D-14) -- `assemble_benchmark_record` never
            invents an empty block for it.
        solver_config: Caller-supplied dict describing the solver
            configuration in force (e.g. `robust_loss`, `loss_scale`,
            `refine_intrinsics`). Passed through unmodified.
        accuracy: Caller-supplied dict of accuracy metrics already computed by
            the pipeline (D-06: copied, never recomputed). Passed through
            unmodified.
        environment: The `capture_environment()` output. Passed through
            unmodified.
        memory_readings: `None` (default) when `benchmark_memory` was off for
            this run -- no `"memory"` key appears anywhere in the returned
            record, at the top level or inside any stage block. Otherwise, an
            ordered dict keyed by boundary name in temporal order (starting
            with `"_baseline"`), each value the `capture_peak_memory()`
            reading taken at that boundary (D-18).

    Returns:
        A fully JSON-serializable dict with top-level keys `schema_version`,
        `problem_shape`, `stages`, `solver_config`, `accuracy`, `environment`,
        and (only when `memory_readings` is not `None`) `memory`.
    """
    stages: dict[str, dict] = {}
    for stage_name, diag in diagnostics.items():
        diag_dict = {
            field_name: _to_native(field_value)
            for field_name, field_value in dataclasses.asdict(diag).items()
        }
        stage_entry = dict(diag_dict)
        seconds, seconds_reason = _resolve_stage_seconds(stage_name, timings)
        stage_entry["seconds"] = seconds
        if seconds_reason is not None:
            stage_entry["seconds_reason"] = seconds_reason

        n_params = diag_dict.get("n_params")
        n_groups = diag_dict.get("n_groups")
        stage_entry["fd_reduction"] = (
            n_params / n_groups
            if n_params is not None and n_groups is not None and n_groups != 0
            else None
        )

        stages[stage_name] = stage_entry

    record: dict = {
        "schema_version": schema_version,
        "problem_shape": _to_native(problem_shape),
        "stages": stages,
        "solver_config": _to_native(solver_config),
        "accuracy": _to_native(accuracy),
        "environment": _to_native(environment),
    }

    if memory_readings is not None:
        previous_reading = memory_readings.get("_baseline")
        for boundary_name, reading in memory_readings.items():
            if boundary_name == "_baseline":
                continue

            delta_bytes = None
            if (
                reading.get("peak_bytes") is not None
                and previous_reading is not None
                and previous_reading.get("peak_bytes") is not None
            ):
                delta_bytes = reading["peak_bytes"] - previous_reading["peak_bytes"]

            memory_block = {
                "cumulative_peak_bytes_as_of_stage_end": reading.get("peak_bytes"),
                "delta_bytes_since_previous_boundary": delta_bytes,
                "mode": reading.get("mode"),
                "commit_current_bytes_as_of_stage_end": reading.get(
                    "commit_current_bytes"
                ),
                "commit_peak_bytes_as_of_stage_end": reading.get("commit_peak_bytes"),
                "ram_total_bytes": reading.get("ram_total_bytes"),
            }

            if boundary_name in record["stages"]:
                record["stages"][boundary_name]["memory"] = memory_block
            else:
                # No exact stage match. Before declaring "no solver diagnostics",
                # check whether this is an AGGREGATE boundary whose solver work
                # was recorded under per-item sub-stage keys — e.g. the single
                # "auxiliary_registration" memory boundary spanning the per-camera
                # "auxiliary_registration_<cam>" diagnostics stages. Claiming no
                # least_squares ran there would be false (D-14/D-15: never invent).
                sub_stages = sorted(
                    s for s in record["stages"] if s.startswith(boundary_name + "_")
                )
                if sub_stages:
                    reason = (
                        f"aggregate boundary spanning {len(sub_stages)} "
                        f"sub-stage(s) ({', '.join(sub_stages)}); solver "
                        "diagnostics are recorded per sub-stage, not at this "
                        "aggregate boundary"
                    )
                else:
                    reason = _STAGES_WITH_NO_SOLVER_DIAGNOSTICS_REASON
                record["stages"][boundary_name] = {
                    "seconds": timings.get(boundary_name),
                    "solver_diagnostics_reason": reason,
                    "memory": memory_block,
                }

            previous_reading = reading

        record["memory"] = {
            "whole_run_peak_bytes": (
                previous_reading.get("peak_bytes")
                if previous_reading is not None
                else None
            ),
            "mode": previous_reading.get("mode")
            if previous_reading is not None
            else None,
        }

    return record


def write_benchmark_json(record: dict, path: Path) -> None:
    """Write an `assemble_benchmark_record()` result to disk as JSON.

    Mirrors `aquacal.validation.conditioning`'s existing `json.dump(...,
    indent=2)` writer style, and reuses the overwrite-warning discipline
    already established for `internals/` artifacts (`warn_if_overwriting`),
    even though `benchmark.json` itself lives directly under `output_dir`.

    Args:
        record: The dict returned by `assemble_benchmark_record()`.
        path: Destination file path (typically `output_dir / "benchmark.json"`).
    """
    path = Path(path)
    warn_if_overwriting(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(record, f, indent=2, sort_keys=True)
