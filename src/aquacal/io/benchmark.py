"""Environment and peak-memory capture for benchmark.json (BENCH-02, BENCH-04).

Both public functions in this module are pure, side-effect-free capture
primitives: they read process/OS/dependency state and return a plain dict of
natively-typed values. Neither function writes a file or touches the
calibration pipeline or config -- that wiring belongs to a later plan.

Both functions are designed to never raise, regardless of platform or which
optional dependencies are installed, because a benchmark measurement must
never be the reason a calibration run fails (D-05).
"""

from __future__ import annotations

import importlib.metadata
import logging
import os
import platform
import subprocess
import tracemalloc
from pathlib import Path

import cv2
import numpy as np
import scipy

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
            - `aquacal_version` (str): always a non-empty string.
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

    try:
        import psutil

        env["cpu_count_logical"] = psutil.cpu_count(logical=True)
        env["ram_total_bytes"] = int(psutil.virtual_memory().total)
    except Exception:
        logger.debug(
            "psutil unavailable; cpu_count_logical/ram_total_bytes left as None."
        )

    cwd = (
        repo_hint_path
        if repo_hint_path is not None
        else _find_git_root(Path(__file__).resolve().parent)
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
    to `{"peak_bytes": None, "mode": "unavailable"}` on any unexpected
    error, because a memory measurement must never abort a calibration run.

    Returns:
        Dict with exactly two keys:
            - `peak_bytes` (int | None): the reading, in bytes.
            - `mode` (str): one of `"psutil_peak_wset"`,
              `"proc_status_vmhwm"`, `"tracemalloc_python_heap"`,
              `"psutil_rss_sampled"`, or `"unavailable"`. Distinguishes a
              true OS-maintained high-water mark from the weaker
              instantaneous `"psutil_rss_sampled"` fallback -- never
              conflate the two.
    """
    try:
        system = platform.system()

        if system == "Linux":
            vmhwm_bytes = _linux_vmhwm_bytes()
            if vmhwm_bytes is not None:
                return {"peak_bytes": vmhwm_bytes, "mode": "proc_status_vmhwm"}

        if system == "Windows":
            try:
                import psutil

                peak_wset = psutil.Process().memory_full_info().peak_wset
                return {"peak_bytes": int(peak_wset), "mode": "psutil_peak_wset"}
            except ImportError:
                logger.debug(
                    "psutil unavailable on Windows; falling back to tracemalloc."
                )
        elif system != "Linux":
            try:
                import psutil

                rss = psutil.Process().memory_info().rss
                return {"peak_bytes": int(rss), "mode": "psutil_rss_sampled"}
            except ImportError:
                logger.debug(
                    "psutil unavailable on %s; falling back to tracemalloc.", system
                )

        if not tracemalloc.is_tracing():
            tracemalloc.start()
        _, peak_bytes = tracemalloc.get_traced_memory()
        return {"peak_bytes": int(peak_bytes), "mode": "tracemalloc_python_heap"}
    except Exception:
        logger.debug(
            "capture_peak_memory() failed unexpectedly; degrading to unavailable."
        )
        return {"peak_bytes": None, "mode": "unavailable"}
