"""Layout helpers for the optimizer-internals artifact directory.

`output_dir` already contains `diagnostics.json`, the user-facing diagnostics
report. Observability artifacts produced by the Phase 16 hooks (per-stage
calibration dumps, optimization traces, conditioning diagnostics) are kept in a
separate `internals/` subdirectory rather than a `diagnostics/` directory of
the same level, so that `internals/` reads unambiguously as "optimizer guts
exposed for inspection, not part of normal output."
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

INTERNALS_DIRNAME = "internals"


def ensure_internals_dir(output_dir: Path) -> Path:
    """Return (creating if needed) the internals/ subdirectory of an output dir.

    Args:
        output_dir: Calibration run's top-level output directory.

    Returns:
        Path to output_dir/internals/, created if it did not already exist.
    """
    internals_dir = Path(output_dir) / INTERNALS_DIRNAME
    internals_dir.mkdir(parents=True, exist_ok=True)
    return internals_dir


def warn_if_overwriting(path: Path) -> None:
    """Log a warning if `path` already exists and is about to be replaced.

    Repeat runs overwrite artifacts in `internals/` by design, but do so
    loudly: mixing a fresh trace with a stale conditioning file from a
    different config is the failure mode this guards against.

    Args:
        path: File path about to be written.
    """
    path = Path(path)
    if path.exists():
        logger.warning(
            "Overwriting existing internals artifact at %s "
            "(may be stale from a previous config).",
            path,
        )
