"""One suite-level run manifest for the full experimental suite (DRIVER-02, D-19).

The driver invokes this module exactly ONCE, at pre-flight, before stage 1::

    "${GATE_PYTHON}" -m experiments._run_manifest --out "${OUT_DIR}"

It writes `run_manifest.json` into the run's output directory. Pre-flight is
deliberate: a run that dies at stage 3 still has its execution environment
recorded, which is the repudiation failure the suite's six-sha provenance spine
already produced once (audit finding F-001 -- six shas across the artifacts of a
single "run", and no single anchor saying which code actually ran).

This is a Python emitter rather than a few lines of bash because bash cannot
read NumPy/SciPy/OpenCV build strings reliably, and because a module is
importable by `experiments/check_rerun_gates.py` (which verifies the manifest
under D-21) and by this plan's tests.

Why `installed_distribution_version` is named that, and is NOT authoritative
---------------------------------------------------------------------------
Audit finding **F-002**: `importlib.metadata.version("aquacal")` reports the
last *built* version, not the code that ran. Under an editable or source
install it does not move until the next `pip install -e .`, so every commit
after a release tag reports the tag's bare version -- `2.0.1` for all 156+
commits since `v2.0.1`, exactly as two different commits once both reported
`1.8.0`. Resolving the field from distribution metadata therefore does not fix
F-002; only naming it honestly does. The authoritative fields are `git_sha`
(exact) and `git_describe` (human-readable, and unable to collide across
commits because it carries a commit count and an abbreviated sha).

Per D-45 this module does NOT change the provenance schema in
`src/aquacal/io/benchmark.py`. Touching every artifact writer days before a
freeze risks the run itself, to fix fields this manifest supersedes.

Why the manifest is written once and never appended to (D-19)
-------------------------------------------------------------
End-of-run timing is deliberately NOT appended here. The driver's
`*_state.tsv` already stamps an ISO start and completion per stage, so per-stage
and total wall clock are recoverable from it without making the manifest
mutable mid-run. Do not add an "end-of-run update" step: a manifest that is
rewritten while the suite runs is a manifest whose contents depend on whether
the suite finished.

The OpenCV build suffix
-----------------------
`cv2.__version__` reports `4.13.0` for both the `4.13.0.90` and `4.13.0.92`
PyPI builds. This manifest is the sole owner of that ambiguity (D-20): it
records `opencv_version` (the `cv2` string, for continuity with
`capture_environment`) alongside `opencv_build` (the distribution version,
which keeps the suffix).
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from aquacal.io import capture_environment

logger = logging.getLogger(__name__)

RUN_MANIFEST_FILENAME = "run_manifest.json"

MANIFEST_SCHEMA_VERSION = 1

#: Exactly the fields D-20 requires. `check_rerun_gates.py` imports this tuple
#: rather than keeping a second copy -- two lists of required fields is the
#: drift D-05 exists to prevent.
REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "git_sha",
    "git_describe",
    "git_dirty",
    "os",
    "kernel",
    "machine",
    "python_version",
    "numpy_version",
    "scipy_version",
    "opencv_version",
    "opencv_build",
    "cpu_model",
    "cpu_count_logical",
    "ram_total_bytes",
    "installed_distribution_version",
    "utc_start",
)

#: Tried in order. `opencv-contrib-python` and `opencv-python-headless` are both
#: ABSENT on the box that runs the suite (verified 2026-08-18), so the chain is
#: defensive against a reviewer's environment, not speculative about ours.
_OPENCV_DISTRIBUTIONS = (
    "opencv-python",
    "opencv-contrib-python",
    "opencv-python-headless",
)

#: `git describe` is restricted to VERSION tags. This repository also carries
#: non-version tags -- `pre-rerun-baseline` is created by this very phase -- and
#: an unrestricted `--tags` would anchor the manifest to whichever tag happened
#: to be nearest, silently replacing the semantic version anchor D-18 asks for.
_VERSION_TAG_GLOB = "v[0-9]*"

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_git(args: list[str]) -> str | None:
    """Run a git command in the repository root, or return `None`.

    Never raises: a missing `git`, a non-zero exit, or a directory that is not
    a checkout all degrade to `None`, mirroring `capture_environment`'s
    never-raise contract. Turning a `None` into a failure is Gate 3's job
    (D-21), not this module's.
    """
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        logger.debug("git %s could not be executed", " ".join(args))
        return None
    if completed.returncode != 0:
        logger.debug("git %s exited %d", " ".join(args), completed.returncode)
        return None
    return completed.stdout.strip()


def _resolve_git_describe() -> str | None:
    """D-18's human-readable version anchor: `v2.0.1-161-gd0bbe09`.

    Unlike the installed distribution version, this cannot collide across two
    commits that share a tag -- it carries the commit count and an abbreviated
    sha.
    """
    return _run_git(
        ["describe", "--tags", "--long", "--dirty", "--match", _VERSION_TAG_GLOB]
    )


def _resolve_git_dirty() -> bool | None:
    """Whether the working tree has uncommitted changes to TRACKED files.

    Untracked files are excluded (`--untracked-files=no`) so this agrees with
    the `-dirty` suffix `git describe` appends, which likewise ignores them.
    Recorded post-hoc only: D-47 cut the dirty-tree pre-flight REFUSAL, because
    `experiments/results/` is tracked and the run dirties its own tree, so a
    refusal would kill every resume after the first crash.
    """
    status = _run_git(["status", "--porcelain", "--untracked-files=no"])
    if status is None:
        return None
    return bool(status.strip())


def _resolve_opencv_build() -> str | None:
    """The OpenCV PyPI build string, e.g. `4.13.0.90` (D-20).

    `cv2.__version__` drops the trailing build component, which is what makes
    `.90` and `.92` indistinguishable in every existing artifact.
    """
    for distribution in _OPENCV_DISTRIBUTIONS:
        try:
            return importlib.metadata.version(distribution)
        except Exception:
            continue
    logger.debug("No OpenCV distribution found in installed metadata.")
    return None


def _resolve_installed_distribution_version() -> str | None:
    """The `aquacal` distribution version -- see this module's F-002 note.

    NOT the code that ran. `git_sha` and `git_describe` are the authoritative
    fields; this one is recorded because a mismatch between it and
    `git_describe` is itself evidence (a stale editable install).
    """
    try:
        return importlib.metadata.version("aquacal")
    except Exception:
        logger.debug("Could not resolve the installed aquacal distribution version.")
        return None


def _utc_now_iso_z() -> str:
    """UTC timestamp as `YYYY-MM-DDTHH:MM:SSZ`."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_run_manifest() -> dict:
    """Build the suite-level run manifest payload (D-20).

    Built on top of `aquacal.io.capture_environment`, reusing its fields rather
    than reimplementing them, then adding the four things it cannot record:
    `git_describe`, `git_dirty`, `opencv_build`, and an honestly named
    `installed_distribution_version`.

    Returns:
        A JSON-serialisable dict carrying at least every name in
        `REQUIRED_MANIFEST_FIELDS`. Any field whose source is unavailable is
        `None` rather than absent -- the emitter never raises, and Gate 3 is
        what turns a `None` into a FAIL (D-21).
    """
    env = capture_environment()

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "git_sha": env.get("git_sha"),
        "git_sha_source": env.get("git_sha_source"),
        "git_describe": _resolve_git_describe(),
        "git_dirty": _resolve_git_dirty(),
        "os": env.get("os"),
        "kernel": platform.release(),
        "machine": platform.node(),
        "python_version": env.get("python_version"),
        "numpy_version": env.get("numpy_version"),
        "scipy_version": env.get("scipy_version"),
        "opencv_version": env.get("opencv_version"),
        "opencv_build": _resolve_opencv_build(),
        "cpu_model": env.get("cpu_model"),
        "cpu_count_logical": env.get("cpu_count_logical"),
        "ram_total_bytes": env.get("ram_total_bytes"),
        # F-002: the last BUILT version, never "the code that ran".
        "installed_distribution_version": _resolve_installed_distribution_version(),
        "aquacal_version_declared": env.get("aquacal_version_declared"),
        "utc_start": _utc_now_iso_z(),
    }
    return manifest


def write_run_manifest(out_dir: Path | str, force: bool = False) -> Path:
    """Write `run_manifest.json` into `out_dir` and return its path.

    Args:
        out_dir: The run's output directory. Created if absent.
        force: Overwrite an existing manifest. Off by default: under D-19 the
            manifest is written ONCE at pre-flight and is not mutable mid-run,
            so a second write is a bug (a stage re-invoking the emitter) until
            an operator says otherwise.

    Returns:
        The path written.

    Raises:
        FileExistsError: A manifest already exists and `force` is False.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / RUN_MANIFEST_FILENAME

    if path.exists() and not force:
        raise FileExistsError(
            f"{path} already exists. The run manifest is written once at "
            "pre-flight and is not mutable mid-run (D-19). Pass --force only "
            "if you are deliberately re-basing this run's provenance."
        )

    manifest = build_run_manifest()
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    """Build this module's CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m experiments._run_manifest",
        description="Emit the suite-level run manifest (DRIVER-02, D-19/D-20).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Run output directory to write run_manifest.json into.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite an existing manifest. The manifest is written once at "
            "pre-flight (D-19); this is the explicit override."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 if the manifest was not written.

    Pre-flight is the one place where a failure aborts the suite (D-03), so
    this must report honestly rather than degrading to a warning.
    """
    args = build_arg_parser().parse_args(argv)
    try:
        path = write_run_manifest(args.out, force=args.force)
    except (FileExistsError, OSError) as exc:
        print(f"ERROR: could not write the run manifest: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote run manifest: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
