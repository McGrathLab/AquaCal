"""The environment lockfile artifact for the full experimental suite (D-13).

The driver invokes this module beside `_run_manifest.py` at pre-flight::

    "${GATE_PYTHON}" -m experiments._env_lock --out "${OUT_DIR}"

It writes `environment_lock.txt` into the run's output directory.

Why this is an ARTIFACT and not a committed lockfile (D-13)
-----------------------------------------------------------
Every version that actually moves a number is ALREADY in `run_manifest.json`:
`python_version`, `numpy_version`, `scipy_version`, `opencv_version`,
`opencv_build`, `installed_distribution_version`, `cpu_model`,
`cpu_count_logical`, `ram_total_bytes`, `os`, `kernel`, `machine`, `git_sha`,
`git_describe` and `git_dirty`. What this lock adds is the TRANSITIVE set --
matplotlib, pandas, tqdm and everything under them -- which is worth recording
but is not worth a commit inside the freeze window and the forced second tag
that would follow it (D-04). Capturing it at run time also means it describes
the environment that actually ran, which a pre-freeze commit could not.

Correspondingly, this module does **NOT** tighten `pyproject.toml` or
`requirements.txt`. Those files are the shipped package's dependency contract;
pinning NumPy exactly there would degrade AquaCal for every pip user to serve
one internal run. The one hard pin that exists -- `opencv-python==4.13.*` --
predates this phase and is there for a measured reason (4.14.0 detects 1.95%
fewer corners and moves reconstruction RMSE +7.8%). D-26 makes that pin the
single most important line in the emitted lock, because the target box's
pre-existing environment carries exactly the excluded 4.14.0.

Why a failed freeze is not a refusal (D-13, P26-D-50)
-----------------------------------------------------
`run_stage_preflight`'s run-manifest call site turns a non-zero exit into a
refusal with NO override, because every artifact's provenance anchors to the
manifest. The lock is not in that class: it is supplementary detail on top of a
manifest that already carries the load-bearing versions. So a `pip freeze` that
fails writes the REASON in place of the body and still returns 0. Phase 26's
§ D cut three pre-flight refusals and P26-D-50 binds every survivor to print an
override flag -- adding a fourth refusal here is out of scope (D-12).

The OpenBLAS note
-----------------
D-13 also asks for the OpenBLAS build, which `pip freeze` cannot give: it names
wheels, not the BLAS compiled into them. It is read here from
`numpy.show_config(mode="dicts")`, degrading to a recorded reason when that call
is unavailable. Emitting it is this module's job; CONFIRMING it on the Linux
target is plan 27-12's.
"""

from __future__ import annotations

import argparse
import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ENVIRONMENT_LOCK_FILENAME = "environment_lock.txt"

LOCK_SCHEMA_VERSION = 1

#: Written in place of a body/field whose source could not be read. The word
#: "unavailable" is the contract the tests assert on: never an empty file, and
#: never a silently missing section.
_UNAVAILABLE_PREFIX = "UNAVAILABLE"

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_pip_freeze() -> str | None:
    """Return `pip freeze` output for the RUNNING interpreter, or `None`.

    Invoked as `sys.executable -m pip freeze` rather than a bare `pip`, so the
    lock describes the interpreter that is actually running the suite instead
    of whatever `pip` happens to be first on PATH. On the target that
    distinction is load-bearing: D-28 records that conda is not initialised for
    non-interactive SSH, so a bare `pip` there is the system one.

    Never raises. A missing executable, a non-zero exit, or a `pip` that is not
    installed all degrade to `None`, mirroring `_run_manifest._run_git`'s
    never-raise contract. Turning that `None` into a failure is nobody's job
    here -- D-13 makes this an artifact, not a refusal.
    """
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        logger.debug("pip freeze could not be executed under %s", sys.executable)
        return None
    if completed.returncode != 0:
        logger.debug("pip freeze exited %d", completed.returncode)
        return None
    return completed.stdout.strip()


def _resolve_blas_build() -> str | None:
    """The BLAS/OpenBLAS build NumPy was linked against, or `None`.

    `pip freeze` names wheels, not the BLAS compiled into them, so this is the
    half of D-13's "prose note naming the Python version and the OpenBLAS
    build" that the freeze cannot supply.

    Never raises: an older NumPy without `show_config(mode=...)`, or a config
    dict shaped differently, degrades to `None` with a logged reason.
    """
    try:
        import numpy

        config = numpy.show_config(mode="dicts")
        blas = (config or {}).get("Build Dependencies", {}).get("blas", {})
        if not blas:
            logger.debug("numpy.show_config reported no blas build dependency.")
            return None
        name = blas.get("name")
        version = blas.get("version")
        configuration = blas.get("openblas configuration")
        parts = [f"name={name}", f"version={version}"]
        if configuration:
            parts.append(f"openblas_configuration={configuration}")
        return "; ".join(parts)
    except Exception as exc:  # pragma: no cover - defensive, environment-shaped
        logger.debug("Could not resolve the BLAS build: %s", exc)
        return None


def _utc_now_iso_z() -> str:
    """UTC timestamp as `YYYY-MM-DDTHH:MM:SSZ` -- `_run_manifest`'s format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_environment_lock_text() -> str:
    """Build the lockfile body: a provenance header, then `pip freeze`.

    Returns:
        The full text to write. Never empty, and never missing a section: an
        unresolvable source is written as an `UNAVAILABLE: <reason>` line
        rather than omitted, the same "None, never absent" rule
        `_run_manifest.build_run_manifest` states.
    """
    blas = _resolve_blas_build()
    freeze = _run_pip_freeze()

    header = [
        "# AquaCal suite environment lock (D-13).",
        "# A RUN ARTIFACT, not a committed lockfile: every version that moves a",
        "# number is already in run_manifest.json; this adds the transitive set.",
        f"# lock_schema_version: {LOCK_SCHEMA_VERSION}",
        f"# utc_captured: {_utc_now_iso_z()}",
        f"# sys.executable: {sys.executable}",
        f"# python_version: {platform.python_version()}",
        f"# sys.version: {sys.version.splitlines()[0]}",
        f"# platform: {platform.platform()}",
        "# blas_build: "
        + (
            blas
            if blas is not None
            else f"{_UNAVAILABLE_PREFIX}: numpy.show_config(mode='dicts') "
            "could not be read"
        ),
        "#",
        "# Below: `{executable} -m pip freeze`".format(executable=sys.executable),
        "",
    ]

    if freeze is None:
        body = (
            f"{_UNAVAILABLE_PREFIX}: `pip freeze` could not be read for "
            f"{sys.executable} (missing pip, non-zero exit, or the executable "
            "could not be launched). The lockfile is an artifact and never "
            "refuses a run (D-13); the load-bearing versions remain in "
            "run_manifest.json."
        )
    else:
        body = freeze

    return "\n".join(header) + body.rstrip() + "\n"


def write_environment_lock(out_dir: Path | str, force: bool = False) -> Path:
    """Write `environment_lock.txt` into `out_dir` and return its path.

    Args:
        out_dir: The run's output directory. Created if absent.
        force: Overwrite an existing lockfile. Off by default, matching
            `write_run_manifest`: the lock is captured ONCE at pre-flight
            beside the manifest, so a second write is a bug (a stage
            re-invoking the emitter) until an operator says otherwise.

    Returns:
        The path written.

    Raises:
        FileExistsError: A lockfile already exists and `force` is False.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ENVIRONMENT_LOCK_FILENAME

    if path.exists() and not force:
        raise FileExistsError(
            f"{path} already exists. The environment lock is captured once at "
            "pre-flight beside the run manifest (D-13). Pass --force only if "
            "you are deliberately re-basing this run's environment record."
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(build_environment_lock_text())
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    """Build this module's CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m experiments._env_lock",
        description="Emit the suite environment lockfile artifact (D-13).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Run output directory to write environment_lock.txt into.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite an existing lockfile. The lock is captured once at "
            "pre-flight (D-13); this is the explicit override."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 only if the WRITE failed.

    A failed `pip freeze` is NOT a failure here: the body records the reason and
    this still returns 0, because D-13 makes the lock an artifact rather than a
    pre-flight refusal. Only an unwritable path (or an unforced re-write) is
    reported non-zero, and the driver's call site does not abort on it.
    """
    args = build_arg_parser().parse_args(argv)
    try:
        path = write_environment_lock(args.out, force=args.force)
    except (FileExistsError, OSError) as exc:
        print(f"ERROR: could not write the environment lock: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote environment lock: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
